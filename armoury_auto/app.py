"""Armoury Auto - switches the ASUS Armoury Crate mode (Silent / Performance / Turbo) and
GPU mode (Eco / Standard) automatically from usage rules in config.json, and lives in the
system tray.

    pythonw app.py            run in the tray
    python app.py --status    show current usage and which rule would apply
    python app.py --dry-run   run in the console, log decisions but never switch
    python app.py --set turbo switch once and exit
"""
import argparse
import ctypes
import json
import logging
import os
import sys
import threading
import time
import winreg
from collections import deque
from ctypes import wintypes
from datetime import datetime
from datetime import time as dtime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import psutil

from asus_acpi import GPU_MODES, MODES, AsusAcpi, PowerPlans
from gpu import GpuLoad, dgpu_apps

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
LOG_PATH = HERE / "armoury_auto.log"
STATE_PATH = HERE / "state.json"  # things toggled from the tray that survive restarts
APP_NAME = "ArmouryAuto"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
MODE_COLORS = {"silent": (46, 160, 67), "performance": (33, 118, 255), "turbo": (230, 57, 70), None: (120, 120, 120)}
RULE_KEYS = {"name", "mode", "gpu", "enabled", "apps", "match", "on_battery", "plugged_in", "battery_below",
             "cpu_above", "cpu_below", "gpu_above", "for_seconds", "idle_minutes", "between", "days"}
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
BLOCKER_RECHECK_SECONDS = 30

log = logging.getLogger("armoury_auto")
_user32 = ctypes.WinDLL("user32")


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def user_idle_seconds() -> float:
    info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO))
    _user32.GetLastInputInfo(ctypes.byref(info))
    return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000


def foreground_process_name() -> str | None:
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(_user32.GetForegroundWindow(), ctypes.byref(pid))
    try:
        return normalize_app(psutil.Process(pid.value).name())
    except (psutil.Error, ValueError):
        return None


def normalize_app(name: str) -> str:
    name = name.lower()
    return name[:-4] if name.endswith(".exe") else name


def ask_yes_no(text: str) -> bool:
    flags = 0x4 | 0x20 | 0x10000 | 0x40000  # YESNO | ICONQUESTION | SETFOREGROUND | TOPMOST
    return _user32.MessageBoxW(None, text, "Armoury Auto", flags) == 6  # IDYES


class Usage:
    """A snapshot of how the laptop is being used right now, plus recent CPU/GPU history."""

    def __init__(self):
        psutil.cpu_percent(interval=None)  # first call primes the counter
        self.gpu_load = GpuLoad()
        self.started = time.monotonic()
        self.history: dict[str, deque[tuple[float, float]]] = {"cpu": deque(), "gpu": deque()}
        self.running: set[str] = set()
        self.foreground = None
        self.plugged_in = True
        self.battery_percent = 100
        self.idle_seconds = 0.0
        self.now = datetime.now()

    def sample(self) -> None:
        mono = time.monotonic()
        for metric, value in (("cpu", psutil.cpu_percent(interval=None)), ("gpu", self.gpu_load.busiest_percent())):
            samples = self.history[metric]
            samples.append((mono, value))
            while mono - samples[0][0] > 900:
                samples.popleft()
        self.running = {normalize_app(p.info["name"]) for p in psutil.process_iter(["name"]) if p.info["name"]}
        self.foreground = foreground_process_name()
        battery = psutil.sensors_battery()
        self.plugged_in = battery is None or bool(battery.power_plugged)
        self.battery_percent = battery.percent if battery else 100
        self.idle_seconds = user_idle_seconds()
        self.now = datetime.now()

    def avg(self, metric: str, seconds: float) -> float | None:
        """Average % over the last `seconds`, or None until that much history exists."""
        mono = time.monotonic()
        if mono - self.started < seconds:
            return None
        values = [v for t, v in self.history[metric] if mono - t <= seconds]
        return sum(values) / len(values) if values else None

    def latest(self, metric: str) -> float:
        return self.history[metric][-1][1] if self.history[metric] else 0.0


def _parse_hhmm(text: str) -> dtime:
    return datetime.strptime(text, "%H:%M").time()


def _day_matches(days: list[str] | None, now: datetime) -> bool:
    return days is None or DAYS[now.weekday()] in {d.lower()[:3] for d in days}


def rule_matches(rule: dict, u: Usage) -> bool:
    """A rule applies when every condition it lists is true."""
    if "apps" in rule:
        wanted = {normalize_app(a) for a in rule["apps"]}
        pool = {u.foreground} if rule.get("match", "running") == "foreground" else u.running
        if not wanted & pool:
            return False
    if "on_battery" in rule and rule["on_battery"] != (not u.plugged_in):
        return False
    if "plugged_in" in rule and rule["plugged_in"] != u.plugged_in:
        return False
    if "battery_below" in rule and (u.plugged_in or u.battery_percent >= rule["battery_below"]):
        return False
    window = rule.get("for_seconds", 10)
    for key, metric, above in (("cpu_above", "cpu", True), ("cpu_below", "cpu", False), ("gpu_above", "gpu", True)):
        if key in rule:
            avg = u.avg(metric, window)
            if avg is None or (avg <= rule[key] if above else avg >= rule[key]):
                return False
    if "idle_minutes" in rule and u.idle_seconds < rule["idle_minutes"] * 60:
        return False
    if "between" in rule:
        start, end = (_parse_hhmm(t) for t in rule["between"])
        t = u.now.time()
        if not (start <= t < end if start <= end else t >= start or t < end):
            return False
    return _day_matches(rule.get("days"), u.now)


def load_config() -> dict:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("default_mode") not in MODES:
        raise ValueError(f"default_mode must be one of {list(MODES)}")
    if config.get("default_gpu", "eco") not in GPU_MODES:
        raise ValueError(f"default_gpu must be one of {list(GPU_MODES)}")
    for i, rule in enumerate(config.get("rules", []), 1):
        label = rule.get("name", f"rule #{i}")
        if rule.get("mode") not in MODES:
            raise ValueError(f"'{label}': mode must be one of {list(MODES)}")
        if rule.get("gpu", "eco") not in (*GPU_MODES, "ask"):
            raise ValueError(f"'{label}': gpu must be one of {[*GPU_MODES, 'ask']}")
        if unknown := set(rule) - RULE_KEYS:
            raise ValueError(f"'{label}': unknown setting(s) {sorted(unknown)}")
        for t in rule.get("between", []):
            _parse_hhmm(t)
    for reminder in config.get("reminders", []):
        _parse_hhmm(reminder["at"])
    return config


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def decide(config: dict, usage: Usage) -> tuple[str, str, str]:
    """(mode, gpu, reason) from the first matching rule; gpu may be 'ask'."""
    for rule in config["rules"]:
        if rule.get("enabled", True) and rule_matches(rule, usage):
            return rule["mode"], rule.get("gpu", config.get("default_gpu", "eco")), rule.get("name", "rule")
    return config["default_mode"], config.get("default_gpu", "eco"), "default"


class Controller:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.config = load_config()
        self.config_mtime = CONFIG_PATH.stat().st_mtime
        self.acpi = AsusAcpi()
        self.plans = PowerPlans(self.config["power_plans"])
        self.usage = Usage()
        self.expected_plan = self.plans.active()
        self.current = self.plans.mode_of(self.expected_plan)
        self.gpu = self.expected_gpu = self.acpi.gpu_mode()
        self.reason = "starting"
        self.lock_mode: str | None = None
        self.paused_until = 0.0
        self.last_switch = 0.0
        self.last_gpu_switch = 0.0
        self.power_session = 0           # bumps on every plug / unplug
        self.dgpu_on_charger: bool | None = None  # answer to the plug-in question
        self.asking = False
        self.gpu_blockers: list[str] = []
        self.next_blocker_check = 0.0
        self.force_eco = False
        self.reminders_fired: set[tuple] = set()
        self.enabled = load_state().get("enabled", True)
        self.on_change = lambda: None
        self.notify = lambda title, message: None
        self.stop = threading.Event()

    # ----- GPU -----

    @property
    def gpu_control(self) -> bool:
        return self.gpu in GPU_MODES

    def resolve_gpu(self, gpu: str) -> str | None:
        """Turn 'ask' into eco/standard, popping the question once per plug-in."""
        if gpu != "ask":
            return gpu
        if self.dgpu_on_charger is None:
            if not self.asking and self.gpu_control:
                self.asking = True
                threading.Thread(target=self._ask_dgpu, args=(self.power_session,), daemon=True).start()
            return None
        return "standard" if self.dgpu_on_charger else "eco"

    def _ask_dgpu(self, session: int) -> None:
        answer = ask_yes_no("Charger connected - Turbo mode is on.\n\n"
                            "Turn on the NVIDIA RTX GPU too (Standard GPU mode)?\n\n"
                            "Yes = games / heavy work at full power\n"
                            "No = keep it off (Eco): cooler, quieter, less power")
        self.asking = False
        if session == self.power_session:
            self.dgpu_on_charger = answer
            log.info("Plug-in question answered: NVIDIA GPU %s", "on" if answer else "off")

    def apply_gpu(self, target: str | None, reason: str) -> None:
        if not self.gpu_control or target is None or target == self.gpu:
            if self.gpu_blockers and target != "eco":
                self.gpu_blockers = []
                self.on_change()
            return
        mono = time.monotonic()
        if mono - self.last_gpu_switch < self.config.get("min_minutes_between_gpu_switches", 3) * 60:
            return
        if target == "eco" and not self.force_eco:
            if mono < self.next_blocker_check:
                return
            safe = {normalize_app(a) for a in self.config.get("gpu_safe_to_cut_apps", [])}
            blockers = [a for a in dgpu_apps() if normalize_app(a) not in safe]
            if blockers:
                self.next_blocker_check = mono + BLOCKER_RECHECK_SECONDS
                if blockers != self.gpu_blockers:
                    log.info("Waiting to turn off NVIDIA GPU; in use by %s", ", ".join(blockers))
                    self.notify("Waiting to turn off NVIDIA GPU", "Close: " + ", ".join(blockers)[:180])
                self.gpu_blockers = blockers
                self.on_change()
                return
        if self.dry_run:
            log.info("[dry run] would switch GPU %s -> %s (%s)", self.gpu, target, reason)
        else:
            self.acpi.set_gpu(target)
            log.info("GPU %s -> %s (%s)", self.gpu, target, reason)
            if self.config.get("notify_on_switch", True):
                self.notify(f"GPU: {target.title()}", "NVIDIA GPU " + ("off" if target == "eco" else "on") + f" ({reason})")
        self.gpu = self.expected_gpu = target
        self.last_gpu_switch = mono
        self.force_eco = False
        self.gpu_blockers = []
        self.on_change()

    # ----- performance mode -----

    def apply(self, mode: str, reason: str) -> None:
        self.reason = reason
        if mode == self.current:
            return
        if self.dry_run:
            log.info("[dry run] would switch %s -> %s (%s)", self.current, mode, reason)
        else:
            self.acpi.set_mode(mode)
            if guid := self.plans.by_mode.get(mode):
                self.plans.set_active(guid)
                self.expected_plan = guid
            log.info("Switched %s -> %s (%s)", self.current, mode, reason)
            if self.config.get("notify_on_switch", True):
                self.notify(f"{mode.title()} mode", reason)
        self.current = mode
        self.last_switch = time.monotonic()
        self.on_change()

    # ----- manual changes, reminders, config -----

    def detect_manual_change(self) -> None:
        """Fn+F5, Armoury Crate or the Windows power menu changed things behind our back."""
        changes = []
        active = self.plans.active()
        if active != self.expected_plan:
            self.expected_plan = active
            mode = self.plans.mode_of(active)
            if mode and mode != self.current:
                self.current = mode
                changes.append(f"{mode.title()} mode")
        gpu = self.acpi.gpu_mode()
        if gpu != self.expected_gpu:
            self.gpu = self.expected_gpu = gpu
            changes.append(f"GPU {gpu.title() if gpu else 'unknown'}")
            if gpu == "ultimate":
                self.notify("GPU set to Ultimate", "Automatic GPU switching is off while Ultimate is on")
        if not changes:
            return
        self.lock_mode = None
        minutes = self.config.get("respect_manual_change_minutes", 0)
        log.info("Manual change detected (%s); pausing rules for %s min", ", ".join(changes), minutes)
        if minutes:
            self.paused_until = time.monotonic() + minutes * 60
            self.reason = "manual change"
            self.notify("Manual change: " + ", ".join(changes), f"Automatic switching paused for {minutes} min")
        self.on_change()

    def check_reminders(self) -> None:
        now = self.usage.now
        for i, reminder in enumerate(self.config.get("reminders", [])):
            key = (now.date(), i)
            if (key not in self.reminders_fired and _day_matches(reminder.get("days"), now)
                    and now.strftime("%H:%M") == reminder["at"]):
                self.reminders_fired.add(key)
                log.info("Reminder: %s", reminder["message"])
                self.notify(reminder.get("title", "Reminder"), reminder["message"])

    def reload_config_if_changed(self) -> None:
        mtime = CONFIG_PATH.stat().st_mtime
        if mtime == self.config_mtime:
            return
        self.config_mtime = mtime
        try:
            self.config = load_config()
            self.plans = PowerPlans(self.config["power_plans"])
            log.info("Reloaded config.json")
            self.notify("Config reloaded", f"{len(self.config['rules'])} rules active")
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            log.error("config.json is invalid, keeping previous rules: %s", e)
            self.notify("config.json has an error", str(e)[:200])

    def set_enabled(self, enabled: bool) -> None:
        """Turn the whole app on/off from the tray; remembered across restarts."""
        self.enabled = enabled
        save_state({**load_state(), "enabled": enabled})
        if enabled:
            # Whatever changed while off is the new baseline, not a "manual change".
            self.expected_plan = self.plans.active()
            self.current = self.plans.mode_of(self.expected_plan)
            self.gpu = self.expected_gpu = self.acpi.gpu_mode()
            self.lock_mode = None
            self.resume()
        log.info("Automatic switching %s", "enabled" if enabled else "disabled")
        self.notify("Armoury Auto " + ("on" if enabled else "off"),
                    "Automatic switching resumed" if enabled else
                    "Nothing will be switched until you turn it back on from the tray")
        self.on_change()

    def pause_for(self, minutes: int) -> None:
        self.paused_until = time.monotonic() + minutes * 60
        log.info("Paused for %s min from the tray", minutes)
        self.on_change()

    @property
    def paused(self) -> bool:
        return time.monotonic() < self.paused_until

    def resume(self) -> None:
        self.paused_until = self.last_switch = self.last_gpu_switch = self.next_blocker_check = 0.0

    def tick(self) -> None:
        self.reload_config_if_changed()
        if not self.enabled:
            return
        was_plugged_in = self.usage.plugged_in
        self.usage.sample()
        if self.usage.plugged_in != was_plugged_in:
            log.info("Power source changed: %s", "plugged in" if self.usage.plugged_in else "on battery")
            self.power_session += 1
            self.dgpu_on_charger = None
            self.resume()  # react to plugging in / unplugging immediately
        self.detect_manual_change()
        self.check_reminders()
        if self.paused:
            return
        mode, gpu, reason = decide(self.config, self.usage)
        if self.lock_mode:
            mode, reason = self.lock_mode, "locked from tray"
        cooldown = self.config.get("min_seconds_between_switches", 15)
        if mode == self.current or time.monotonic() - self.last_switch >= cooldown:
            self.apply(mode, reason)
        self.apply_gpu(self.resolve_gpu(gpu), reason)

    def run(self) -> None:
        if self.gpu == "ultimate":
            self.notify("GPU is in Ultimate mode", "Automatic GPU switching is off. Set GPU Mode to "
                        "Standard in Armoury Crate and restart to enable it.")
        while not self.stop.is_set():
            try:
                self.tick()
            except Exception:
                log.exception("Error while checking rules")
            self.stop.wait(self.config.get("check_interval_seconds", 3))

    def status_text(self) -> str:
        mode = self.current.title() if self.current else "Unknown"
        if not self.enabled:
            return "OFF - automatic switching disabled"
        if self.lock_mode:
            return f"{mode} - locked"
        if self.paused:
            return f"{mode} - paused ({int((self.paused_until - time.monotonic()) / 60) + 1} min left)"
        return f"{mode} - {self.reason}"

    def gpu_text(self) -> str:
        text = f"GPU: {self.gpu.title() if self.gpu else 'unknown'}"
        if self.gpu == "ultimate":
            return text + " (auto GPU off)"
        if self.gpu_blockers:
            return text + " - waiting for " + ", ".join(self.gpu_blockers)[:60]
        return text


# ---------- Start with Windows ----------

def startup_command() -> str:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    return f'"{pythonw}" "{HERE / "app.py"}"'


def startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, APP_NAME)[0] == startup_command()
    except OSError:
        return False


def set_startup(enabled: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


# ---------- Tray ----------

def make_icon(mode: str | None, dimmed: bool = False, gpu_on: bool = False, off: bool = False):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if off:  # app disabled: hollow grey ring
        draw.ellipse((4, 4, 60, 60), outline=MODE_COLORS[None], width=8)
        draw.line((16, 48, 48, 16), fill=MODE_COLORS[None], width=8)
        return img
    draw.ellipse((2, 2, 62, 62), fill=MODE_COLORS[None] if dimmed else MODE_COLORS.get(mode, MODE_COLORS[None]))
    try:
        font = ImageFont.truetype("segoeuib.ttf", 38)
    except OSError:
        font = ImageFont.load_default(size=38)
    draw.text((32, 33), (mode or "?")[0].upper(), fill="white", font=font, anchor="mm")
    if gpu_on:  # small green dot = NVIDIA GPU powered
        draw.ellipse((42, 42, 63, 63), fill=(118, 185, 0), outline="white", width=3)
    return img


def run_tray(controller: Controller) -> None:
    import pystray
    from pystray import Menu, MenuItem as Item

    def lock(mode):
        def action(icon, item):
            controller.lock_mode = mode
            if mode is None:
                controller.resume()
            refresh()
        return action

    def toggle_dgpu(icon, item):
        controller.dgpu_on_charger = not controller.dgpu_on_charger
        controller.last_gpu_switch = 0.0

    def force_eco(icon, item):
        controller.force_eco = True
        controller.next_blocker_check = 0.0

    def quit_app(icon, item):
        controller.stop.set()
        icon.stop()

    def on(item):  # shows items that only make sense while the app is enabled
        return controller.enabled

    menu = Menu(
        Item(lambda item: controller.status_text(), None, enabled=False),
        Item(lambda item: controller.gpu_text(), None, enabled=False, visible=on),
        Menu.SEPARATOR,
        Item("Enable Armoury Auto", lambda i, it: controller.set_enabled(not controller.enabled),
             checked=on),
        Item("Pause for 1 hour", lambda i, it: controller.pause_for(60),
             visible=lambda i: controller.enabled and not controller.paused),
        Item("Resume rules now", lambda i, it: (controller.resume(), refresh()),
             visible=lambda i: controller.enabled and controller.paused),
        Menu.SEPARATOR,
        Item("Automatic (use rules)", lock(None), checked=lambda i: controller.lock_mode is None, radio=True,
             visible=on),
        *(Item(f"Lock: {m.title()}", lock(m), checked=lambda i, m=m: controller.lock_mode == m, radio=True,
               visible=on)
          for m in ("silent", "performance", "turbo")),
        Menu.SEPARATOR,
        Item("NVIDIA GPU on while charging", toggle_dgpu, checked=lambda i: bool(controller.dgpu_on_charger),
             visible=lambda i: controller.enabled and controller.usage.plugged_in and controller.gpu_control),
        Item("Turn off NVIDIA GPU anyway", force_eco,
             visible=lambda i: controller.enabled and bool(controller.gpu_blockers)),
        Menu.SEPARATOR,
        Item("Edit rules (config.json)", lambda i, it: os.startfile(CONFIG_PATH)),
        Item("Open log", lambda i, it: os.startfile(LOG_PATH)),
        Item("Start with Windows", lambda i, it: set_startup(not startup_enabled()),
             checked=lambda i: startup_enabled()),
        Menu.SEPARATOR,
        Item("Quit", quit_app),
    )
    icon = pystray.Icon(APP_NAME, make_icon(controller.current), "Armoury Auto", menu)

    def refresh():
        icon.icon = make_icon(controller.current, dimmed=controller.paused and not controller.lock_mode,
                              gpu_on=controller.gpu in ("standard", "ultimate"), off=not controller.enabled)
        icon.title = (f"Armoury Auto: {controller.status_text()}"
                      + (f"\n{controller.gpu_text()}" if controller.enabled else ""))[:127]
        icon.update_menu()

    controller.on_change = refresh
    controller.notify = lambda title, message: icon.notify(message, title)

    def setup(icon):
        icon.visible = True
        refresh()
        threading.Thread(target=controller.run, daemon=True).start()

    icon.run(setup)


# ---------- CLI ----------

def print_status() -> None:
    controller = Controller(dry_run=True)
    print("Sampling usage for 3 seconds...")
    controller.usage.sample()
    time.sleep(3)
    u = controller.usage
    u.sample()
    safe = {normalize_app(a) for a in controller.config.get("gpu_safe_to_cut_apps", [])}
    print(f"Current mode     : {controller.current or 'unknown'} (power plan {controller.expected_plan})")
    print(f"GPU mode         : {controller.gpu}")
    print(f"Power            : {'plugged in' if u.plugged_in else 'on battery'}, {u.battery_percent:.0f}%")
    print(f"CPU / GPU load   : {u.latest('cpu'):.0f}% / {u.latest('gpu'):.0f}% (last 3 s)")
    print(f"Foreground app   : {u.foreground}")
    print(f"Idle             : {u.idle_seconds:.0f} s")
    print(f"Apps holding dGPU: {[a for a in dgpu_apps() if normalize_app(a) not in safe] or 'none (safe for Eco)'}")
    print("Rules (top to bottom, first match wins; CPU/GPU rules need their for_seconds of history):")
    for rule in controller.config["rules"]:
        state = "off" if not rule.get("enabled", True) else ("MATCH" if rule_matches(rule, u) else "-")
        print(f"  [{state:>5}] {rule.get('name', '?')} -> {rule['mode']}, GPU {rule.get('gpu', 'default')}")
    mode, gpu, reason = decide(controller.config, u)
    print(f"Would choose     : {mode}, GPU {gpu} ({reason})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-switch ASUS Armoury Crate mode by usage.")
    parser.add_argument("--status", action="store_true", help="show usage and which rule would apply")
    parser.add_argument("--dry-run", action="store_true", help="run in the console without switching")
    parser.add_argument("--set", choices=list(MODES), help="switch to a mode once and exit")
    args = parser.parse_args()

    handlers = [RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=1, encoding="utf-8")]
    if sys.stdout:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=handlers)

    if args.status:
        print_status()
        return
    if args.set:
        plans = PowerPlans(load_config()["power_plans"])
        AsusAcpi().set_mode(args.set)
        if guid := plans.by_mode.get(args.set):
            plans.set_active(guid)
        print(f"Switched to {args.set}")
        return

    ctypes.windll.kernel32.CreateMutexW(None, False, f"Local\\{APP_NAME}")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(None, "Armoury Auto is already running (see the system tray).",
                                         "Armoury Auto", 0x40)
        return

    controller = Controller(dry_run=args.dry_run)
    log.info("Started%s; mode: %s, GPU: %s", " (dry run)" if args.dry_run else "", controller.current, controller.gpu)
    if args.dry_run:
        try:
            controller.run()
        except KeyboardInterrupt:
            pass
    else:
        run_tray(controller)


if __name__ == "__main__":
    main()
