"""PC Performance Predictor: build a PC from real components, predict its
Performance_Score with the trained ML model in real time, estimate game FPS and
download the build as an Excel report.

Run with:  streamlit run app.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import catalog  # noqa: E402
from build import (Build, boards_for_cpu, cases_for_board, check_compatibility,  # noqa: E402
                   coolers_for_cpu, cpus_for_brand, gpus_for_cpu, max_ram_kits,
                   power_draw, psus_for_draw, ram_for_board, recommended_psu_for_draw,
                   to_model_features, total_ram_gb)
from export import build_excel, parts_table  # noqa: E402
from fps import RESOLUTIONS, experience, fps_table  # noqa: E402

MODEL_PATH = ROOT / "models" / "performance_model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"
MAX_SCORE = 1000


@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


@st.cache_data
def load_metrics():
    return json.loads(METRICS_PATH.read_text())


def pick(label, items, key, default_index=0):
    """Selectbox over catalog items; returns the chosen item dict."""
    names = [item["name"] for item in items]
    chosen = st.selectbox(label, names, index=min(default_index, len(names) - 1), key=key)
    return items[names.index(chosen)]


def first_index(items, predicate):
    return next((i for i, item in enumerate(items) if predicate(item)), 0)


def score_label(score: float) -> str:
    if score >= 850:
        return "Very High"
    if score >= 650:
        return "High"
    if score >= 400:
        return "Medium"
    return "Low"


st.set_page_config(page_title="PC Performance Predictor", page_icon="💻", layout="wide")
# Keep the results column in view while scrolling through the parts list
st.markdown("""<style>
div[data-testid="stColumn"]:has(.results-anchor) {
    position: sticky; top: 4.5rem; align-self: flex-start;
}
</style>""", unsafe_allow_html=True)
st.title("💻 PC Performance Predictor")
st.write("Build your PC part by part. Only parts that work with your earlier choices are "
         "shown, and the ML model updates the **Performance Score** live as you change them.")

if not MODEL_PATH.exists():
    st.error("Model not found. Run `python src/train.py` first.")
    st.stop()

model = load_model()
metrics = load_metrics()
tm = metrics["test_metrics"]

with st.sidebar:
    st.header("About the model")
    st.write(f"**Learning type:** {metrics.get('learning_type', 'Supervised learning (regression)')}")
    st.write(f"**Algorithm:** {metrics['best_model']}")
    st.write(f"**R²:** {tm['R2']:.3f}")
    st.write(f"**MAE:** {tm['MAE']:.1f}  ·  **RMSE:** {tm['RMSE']:.1f}")
    st.caption(f"Trained on {metrics['train_rows'] + metrics['test_rows']} cleaned PC "
               f"records; {len(metrics['comparison'])} algorithms compared.")
    st.divider()
    st.header("Catalog")
    st.caption(f"{len(catalog.CPUS)} CPUs · {len(catalog.MOTHERBOARDS)} motherboards · "
               f"{len(catalog.RAM_KITS)} RAM kits · {len(catalog.STORAGE)} drives · "
               f"{len(catalog.GPUS) - 1} GPUs · {len(catalog.COOLERS)} coolers · "
               f"{len(catalog.CASES)} cases · {len(catalog.PSUS)} PSUs")

parts_col, result_col = st.columns([3, 2], gap="large")

with parts_col:
    # --- Processor ---
    st.subheader("Processor")
    brand = st.radio("CPU brand", ["AMD", "Intel"], horizontal=True, key="brand")
    cpu = pick("CPU", cpus_for_brand(catalog.CPUS, brand), "cpu")
    st.caption(f"{cpu['cores']} cores · up to {cpu['boost_ghz']} GHz · socket {cpu['socket']} · "
               f"{cpu['power_w']} W max · "
               f"{'integrated graphics' if cpu['igpu'] else 'no integrated graphics'} · "
               f"{'cooler included' if cpu['stock_cooler'] else 'no cooler included'}")

    # --- Motherboard ---
    st.subheader("Motherboard")
    boards = boards_for_cpu(catalog.MOTHERBOARDS, cpu)
    board = pick(f"Motherboard ({len(boards)} {cpu['socket']} boards)", boards, "board")
    st.caption(f"Socket {board['socket']} · {board['ram_type']} · {board['form_factor']} · "
               f"{board['ram_slots']} RAM slots")

    # --- Memory ---
    st.subheader("Memory")
    c1, c2 = st.columns([3, 1])
    with c1:
        kits = ram_for_board(catalog.RAM_KITS, board)
        ram = pick(f"RAM kit ({board['ram_type']} only)", kits, "ram",
                   default_index=first_index(kits, lambda k: k["capacity_gb"] == 16
                                             and k["sticks"] == 2))
    with c2:
        ram_kits = st.selectbox("Kits", range(1, max_ram_kits(board, ram) + 1), key="ram_qty")
    st.caption(f"Total {ram['capacity_gb'] * ram_kits} GB · "
               f"{ram['sticks'] * ram_kits} of {board['ram_slots']} slots used")

    # --- Storage ---
    st.subheader("Storage")
    c1, c2 = st.columns(2)
    with c1:
        drive1 = pick("Primary drive", catalog.STORAGE, "drive1",
                      default_index=first_index(catalog.STORAGE,
                                                lambda d: d["name"].startswith("Crucial P3 1TB")))
    with c2:
        extra = [{"name": "None", "capacity_gb": 0, "type": "None"}] + catalog.STORAGE
        drive2 = pick("Second drive (optional)", extra, "drive2")
    storage = [drive1] + ([drive2] if drive2["type"] != "None" else [])
    st.caption(f"Total {sum(d['capacity_gb'] for d in storage)} GB")

    # --- Graphics ---
    st.subheader("Graphics card")
    gpus = gpus_for_cpu(catalog.GPUS, cpu)
    gpu = pick("GPU", gpus, "gpu")
    if not cpu["igpu"]:
        st.caption(f"The {cpu['name']} has no integrated graphics, so a graphics card is required.")
    if gpu["power_w"]:
        st.caption(f"Performance tier {gpu['gpu_level']}/12 · {gpu['power_w']} W")

    # --- Cooling & case ---
    st.subheader("Cooling & case")
    c1, c2 = st.columns(2)
    with c1:
        cooler = pick("CPU cooler", coolers_for_cpu(catalog.COOLERS, cpu), "cooler")
        st.caption(f"Handles about {cooler['capacity_w']} W (CPU needs {cpu['power_w']} W)")
    with c2:
        cases = cases_for_board(catalog.CASES, board)
        case = pick(f"Case (fits {board['form_factor']})", cases, "case")
        st.caption(f"Up to {case['max_form_factor']} · {case['airflow'].lower()} airflow")
    case_fans = st.select_slider("Extra case fans", options=catalog.EXTRA_CASE_FANS, value=0,
                                 key="fans", help="Fans added on top of what the case ships with.")

    # --- Power ---
    st.subheader("Power supply")
    draw = power_draw(cpu, gpu)
    recommended = recommended_psu_for_draw(draw)
    psus = psus_for_draw(catalog.PSUS, draw)
    psu = pick(f"PSU (≥ {draw} W shown)", psus, "psu",
               default_index=first_index(psus, lambda p: p["watts"] >= recommended))
    st.caption(f"Estimated peak draw {draw} W · recommended {recommended} W or more")

    # --- Software & condition ---
    st.subheader("Software & condition")
    c1, c2 = st.columns(2)
    with c1:
        os_name = st.selectbox("Operating system", list(catalog.OPERATING_SYSTEMS), key="os")
    with c2:
        age = st.slider("PC age (years)", 0.0, 8.0, 0.0, step=0.5,
                        help="0 for a brand-new build. Older systems lose performance.")

build = Build(cpu=cpu, motherboard=board, ram=ram, ram_kits=int(ram_kits),
              storage=storage, gpu=gpu, psu=psu, cooler=cooler, case=case,
              os_name=os_name, os_family=catalog.OPERATING_SYSTEMS[os_name],
              age_years=age, case_fans=case_fans)
check = check_compatibility(build)
features, notes = to_model_features(build)
temperature = features["Temperature_C"]
fps_df = fps_table(cpu, gpu, total_ram_gb(build), temperature)

score = level = None
if check.ok:
    raw_score = float(model.predict(pd.DataFrame([features]))[0])
    score = round(min(max(raw_score, 0), MAX_SCORE))
    level = score_label(score)

with result_col:
    st.markdown('<div class="results-anchor"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        if check.ok:
            # Show how much the last part change moved the score
            if st.session_state.get("score") != score:
                st.session_state["prev_score"] = st.session_state.get("score")
                st.session_state["score"] = score
            prev = st.session_state.get("prev_score")
            delta = None if prev is None else score - prev

            st.metric("Performance Score", f"{score} / {MAX_SCORE}",
                      delta=None if not delta else f"{delta:+d} from last change")
            st.progress(score / MAX_SCORE, text=f"{level} performance")
            st.caption(f"Typical prediction error: ± {tm['RMSE']:.0f} points.")
            if raw_score > MAX_SCORE:
                st.caption("This build reaches the top of the scale (dataset maximum 1000).")

            report = build_excel(build, score, level, tm["RMSE"], metrics["best_model"],
                                 features, check, temperature, fps_df)
            st.download_button(
                "📥 Download build report (Excel)", data=report,
                file_name=f"pc_build_report_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch")
        else:
            st.info("Fix the issues below to see the prediction.")

    st.subheader("Build check")
    if check.ok and not check.warnings:
        st.success("All parts are compatible.", icon="✅")
    for msg in check.errors:
        st.error(msg, icon="⛔")
    for msg in check.warnings:
        st.warning(msg, icon="⚠️")

    st.write(f"**Power:** ~{draw} W of {psu['watts']} W ({draw / psu['watts']:.0%} load)")
    st.progress(min(draw / psu["watts"], 1.0))
    st.write(f"**Estimated CPU temperature under load:** {temperature:.0f} °C")

    if notes:
        with st.expander(f"ℹ️ {len(notes)} spec(s) beyond the training data"):
            st.write("The model only saw PCs within these ranges, so these values were "
                     "capped:\n\n" + "\n".join(f"- {n}" for n in notes))

st.divider()
fps_tab, parts_tab, model_tab = st.tabs(["🎮 Game FPS", "📋 Parts list", "🔍 What the model sees"])

with fps_tab:
    resolution = st.radio("Resolution", RESOLUTIONS, index=1, horizontal=True, key="res")
    games = fps_df[["Game", "Genre", resolution]].rename(columns={resolution: "Estimated FPS"})
    games["Experience"] = games["Estimated FPS"].map(experience)
    smooth = int((games["Estimated FPS"] >= 60).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Games at 60+ FPS", f"{smooth} / {len(games)}")
    c2.metric("Median FPS", f"{games['Estimated FPS'].median():.0f}")
    c3.metric("Toughest game", f"{games['Estimated FPS'].min()} FPS",
              help=games.loc[games["Estimated FPS"].idxmin(), "Game"])

    st.dataframe(
        games, hide_index=True, width="stretch",
        column_config={"Estimated FPS": st.column_config.ProgressColumn(
            "Estimated FPS", min_value=0, max_value=240, format="%d")})
    st.caption("Rough estimates at High settings, native resolution, no upscaling or frame "
               "generation. The dataset has no FPS data, so these come from GPU/CPU gaming "
               "ratings and per-game reference figures (src/fps.py), not from the ML model. "
               "Elden Ring, Apex Legends and GTA V have engine FPS caps.")

with parts_tab:
    st.dataframe(parts_table(build), hide_index=True, width="stretch")

with model_tab:
    st.caption("The ML model was trained on these 8 attributes, each derived from your parts. "
               "Motherboard, PSU and case decide which parts are compatible; cooler, case "
               "airflow, extra fans and power draw set the estimated temperature.")
    st.dataframe(pd.DataFrame([
        {"Model input": "RAM_GB", "Value": features["RAM_GB"],
         "From": f"{ram_kits} × {ram['name']}"},
        {"Model input": "CPU_Cores", "Value": features["CPU_Cores"], "From": cpu["name"]},
        {"Model input": "Clock_GHz", "Value": features["Clock_GHz"],
         "From": f"{cpu['name']} (max boost {cpu['boost_ghz']} GHz)"},
        {"Model input": "GPU_Level", "Value": features["GPU_Level"], "From": gpu["name"]},
        {"Model input": "Storage_GB", "Value": features["Storage_GB"],
         "From": " + ".join(d["name"] for d in storage)},
        {"Model input": "Temperature_C", "Value": features["Temperature_C"],
         "From": f"Estimated: {cooler['name']}, {case['airflow'].lower()}-airflow case, "
                 f"{case_fans} extra fans, {draw} W"},
        {"Model input": "Age_Years", "Value": features["Age_Years"], "From": "PC age slider"},
        {"Model input": "OS", "Value": features["OS"], "From": os_name},
    ]).astype({"Value": str}), hide_index=True, width="stretch")
