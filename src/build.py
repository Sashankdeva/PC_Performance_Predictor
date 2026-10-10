"""Turn a set of selected PC components into model inputs.

The ML model was trained on 8 attributes (RAM_GB, CPU_Cores, GPU_Level,
Storage_GB, Clock_GHz, Age_Years, Temperature_C, OS). This module maps real
components onto those attributes, estimates the operating temperature from the
cooling setup, and checks that the parts are compatible with each other.
"""
from dataclasses import dataclass, field

# Training-data range of each model input; values outside are capped
TRAINING_RANGES = {
    "RAM_GB": (4, 64),
    "CPU_Cores": (2, 16),
    "GPU_Level": (0, 12),
    "Storage_GB": (128, 2048),
    "Clock_GHz": (2.0, 5.0),
    "Age_Years": (0.0, 8.0),
    "Temperature_C": (40.0, 90.0),
}

FORM_FACTOR_SIZE = {"Mini-ITX": 1, "Micro-ATX": 2, "ATX": 3}
AIRFLOW_PENALTY_C = {"High": 0, "Medium": 4, "Low": 9}
# Each extra case fan lowers temperature a little, with diminishing returns
FAN_COOLING_C = [0, 1.5, 2.5, 3.5, 4.0, 4.5, 5.0]

# Motherboard, RAM, drives and fans
BASE_SYSTEM_POWER_W = 75
# Recommended PSU headroom over the estimated peak draw
PSU_HEADROOM = 1.3
MIN_RECOMMENDED_PSU_W = 450


@dataclass
class Build:
    cpu: dict
    motherboard: dict
    ram: dict
    ram_kits: int
    storage: list
    gpu: dict
    psu: dict
    cooler: dict
    case: dict
    os_name: str
    os_family: str
    age_years: float = 0.0
    case_fans: int = 0


@dataclass
class CheckResult:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def total_ram_gb(build: Build) -> int:
    return build.ram["capacity_gb"] * build.ram_kits


def total_storage_gb(build: Build) -> int:
    return sum(drive["capacity_gb"] for drive in build.storage)


def power_draw(cpu: dict, gpu: dict) -> int:
    """Peak system power draw in watts."""
    return cpu["power_w"] + gpu["power_w"] + BASE_SYSTEM_POWER_W


def estimate_power_draw(build: Build) -> int:
    return power_draw(build.cpu, build.gpu)


def recommended_psu_for_draw(draw_w: int) -> int:
    watts = round(draw_w * PSU_HEADROOM / 50) * 50
    return int(max(watts, MIN_RECOMMENDED_PSU_W))


def recommended_psu_watts(build: Build) -> int:
    return recommended_psu_for_draw(estimate_power_draw(build))


def estimate_temperature(build: Build) -> float:
    """Estimate CPU operating temperature under load (°C).

    Rises with how hard the cooler is pushed (CPU heat / cooler capacity),
    with poor case airflow, and with GPU heat dumped inside the case; extra
    case fans bring it down.
    """
    cooler_load = build.cpu["power_w"] / build.cooler["capacity_w"]
    temp = (38
            + 35 * cooler_load
            + AIRFLOW_PENALTY_C[build.case["airflow"]]
            + build.gpu["power_w"] / 60
            - FAN_COOLING_C[min(build.case_fans, len(FAN_COOLING_C) - 1)])
    return round(min(max(temp, 40.0), 95.0), 1)


# --- Compatible-part filters: each choice narrows the options for the next part ---

def cpu_brand(cpu: dict) -> str:
    return cpu["name"].split()[0]


def cpus_for_brand(cpus: list, brand: str) -> list:
    return [c for c in cpus if cpu_brand(c) == brand]


def boards_for_cpu(boards: list, cpu: dict) -> list:
    return [b for b in boards if b["socket"] == cpu["socket"]]


def ram_for_board(kits: list, board: dict) -> list:
    return [k for k in kits if k["ram_type"] == board["ram_type"]]


def max_ram_kits(board: dict, kit: dict) -> int:
    return max(board["ram_slots"] // kit["sticks"], 1)


def gpus_for_cpu(gpus: list, cpu: dict) -> list:
    """Without integrated graphics the PC needs a graphics card."""
    return [g for g in gpus if cpu["igpu"] or g["power_w"] > 0]


def coolers_for_cpu(coolers: list, cpu: dict) -> list:
    """Offer the stock cooler only for CPUs that ship with one."""
    return [c for c in coolers if cpu["stock_cooler"] or not c["stock"]]


def cases_for_board(cases: list, board: dict) -> list:
    size = FORM_FACTOR_SIZE[board["form_factor"]]
    return [c for c in cases if FORM_FACTOR_SIZE[c["max_form_factor"]] >= size]


def psus_for_draw(psus: list, draw_w: int) -> list:
    return [p for p in psus if p["watts"] >= draw_w]


def check_compatibility(build: Build) -> CheckResult:
    result = CheckResult()
    cpu, board, ram, case = build.cpu, build.motherboard, build.ram, build.case

    if cpu["socket"] != board["socket"]:
        result.errors.append(
            f"CPU socket {cpu['socket']} does not fit the {board['name']} "
            f"(socket {board['socket']}).")

    if ram["ram_type"] != board["ram_type"]:
        result.errors.append(
            f"{ram['ram_type']} memory does not work in the {board['name']}, "
            f"which needs {board['ram_type']}.")

    sticks = ram["sticks"] * build.ram_kits
    if sticks > board["ram_slots"]:
        result.errors.append(
            f"{sticks} RAM sticks selected but the {board['name']} has only "
            f"{board['ram_slots']} slots.")

    if FORM_FACTOR_SIZE[board["form_factor"]] > FORM_FACTOR_SIZE[case["max_form_factor"]]:
        result.errors.append(
            f"The {board['form_factor']} motherboard does not fit in the {case['name']} "
            f"(max {case['max_form_factor']}).")

    if build.gpu["power_w"] == 0 and not cpu["igpu"]:
        result.errors.append(
            f"The {cpu['name']} has no integrated graphics, so a graphics card is "
            "required for display output.")

    if build.cooler["stock"] and not cpu["stock_cooler"]:
        result.errors.append(
            f"The {cpu['name']} is sold without a cooler. Choose an aftermarket cooler.")

    if not build.storage:
        result.errors.append("Select at least one storage drive to install the OS.")

    draw = estimate_power_draw(build)
    if build.psu["watts"] < draw:
        result.errors.append(
            f"PSU too weak: estimated peak draw is {draw} W but the PSU provides "
            f"{build.psu['watts']} W.")
    elif build.psu["watts"] < draw * PSU_HEADROOM:
        result.warnings.append(
            f"PSU headroom is tight ({build.psu['watts']} W for ~{draw} W peak). "
            f"{recommended_psu_watts(build)} W or more is recommended.")

    if cpu["power_w"] > build.cooler["capacity_w"] * 1.1:
        result.warnings.append(
            f"The {build.cooler['name']} is undersized for the {cpu['name']} "
            f"(~{cpu['power_w']} W). Expect high temperatures and thermal throttling.")

    if build.storage and all(d["type"] == "HDD" for d in build.storage):
        result.warnings.append(
            "Only a hard drive is selected. An SSD for the OS makes the system much "
            "more responsive.")

    return result


def to_model_features(build: Build):
    """Map the build to the model's 8 inputs.

    Returns (features, notes): features is a dict ready for the model, notes lists
    any values that were capped to the training-data range.
    """
    raw = {
        "RAM_GB": total_ram_gb(build),
        "CPU_Cores": build.cpu["cores"],
        "GPU_Level": build.gpu["gpu_level"],
        "Storage_GB": total_storage_gb(build),
        "Clock_GHz": build.cpu["boost_ghz"],
        "Age_Years": build.age_years,
        "Temperature_C": estimate_temperature(build),
    }
    features, notes = {}, []
    for key, value in raw.items():
        lo, hi = TRAINING_RANGES[key]
        capped = min(max(value, lo), hi)
        if capped != value:
            notes.append(f"{key} = {value} is outside the training data range "
                         f"({lo}–{hi}); the model uses {capped}.")
        features[key] = capped
    features["OS"] = build.os_family
    return features, notes
