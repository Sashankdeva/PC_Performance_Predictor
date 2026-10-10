# PC Performance Predictor (Team 7)

Build a PC from real components (CPU, motherboard, RAM, SSD/HDD, GPU, PSU, cooler,
case, OS) and predict its **Performance_Score** (0–1000) with a trained ML model.

## Project structure
```
data/                 pc_performance_raw.csv (520 rows), pc_performance_cleaned.csv (503 rows)
src/preprocess.py     raw -> cleaned CSV (types, OS labels, duplicates, ranges, imputation)
src/train.py          compares 9 regression models, saves the best one + metrics + figures
src/catalog.py        component catalog (CPUs, boards, RAM, storage, GPUs, PSUs, coolers, cases)
src/build.py          maps a build to model inputs, estimates temperature, checks compatibility
src/fps.py            rule-based game FPS estimates (12 games, 1080p / 1440p / 4K)
src/export.py         parts table + downloadable Excel report
models/               performance_model.joblib, metrics.json
reports/figures/      model_comparison.png, actual_vs_predicted.png, feature_importance.png
app.py                Streamlit PC builder: choose parts -> compatibility check -> predicted score
```

## How components become model inputs
| Model input | Comes from |
|---|---|
| RAM_GB | RAM kit capacity × number of kits |
| CPU_Cores, Clock_GHz | CPU core count and max boost clock |
| GPU_Level | Graphics card tier (0 = integrated, 12 = flagship) |
| Storage_GB | Total capacity of all drives |
| Temperature_C | Estimated from CPU power vs cooler capacity, case airflow and GPU heat |
| Age_Years | PC age slider (0 for a new build) |
| OS | Windows 10/11 -> Windows; Ubuntu/Mint/Fedora -> Linux |

## Game FPS estimates
The dataset has no FPS data, so FPS is **not** predicted by the ML model. `src/fps.py`
estimates it from each GPU's relative performance (RTX 4090 = 100) and each CPU's gaming
rating (Ryzen 7 9800X3D = 100) against per-game reference figures, taking the lower of the
GPU-limited and CPU-limited FPS. It also adjusts for low RAM and thermal throttling, and
applies engine FPS caps (Elden Ring 60, Apex 300, GTA V 187). Figures are rough estimates
for High settings at native resolution.

## Excel report
The "Download build report" button exports an .xlsx with four sheets: **Summary**
(predicted score, level, compatibility, power, temperature), **Parts** (every selected
component with key specs), **Game FPS** (all games at 1080p / 1440p / 4K) and
**Model Inputs** (the 8 values the ML model received).

## Real-time compatible-part filtering
Each choice narrows the options for the next part, and the score updates live:
- CPU brand (AMD / Intel) -> CPU list
- CPU socket -> motherboards (e.g. AM5 -> AM5 boards only; AM4 -> AM4 boards)
- Motherboard memory type -> RAM kits (AM5 -> DDR5 only), and its slots limit the number of kits
- CPU without integrated graphics -> a graphics card is required; CPU without a bundled cooler -> no stock cooler
- Motherboard form factor -> cases it fits in
- CPU + GPU power draw -> only PSUs strong enough are listed (recommended wattage preselected)

Motherboard, PSU and case are also used for compatibility checks: CPU socket, RAM type,
RAM slots, form factor, PSU wattage vs estimated power draw, stock-cooler availability,
and display output when there is no GPU. Specs beyond the training range (e.g. 24 cores,
6.0 GHz) are capped to the range the model has seen, and the app says so.

## Run
```
pip install -r requirements.txt
python src/preprocess.py
python src/train.py
streamlit run app.py
```

## Inputs
RAM_GB, CPU_Cores, GPU_Level, Storage_GB, Clock_GHz, Age_Years, Temperature_C, OS (Windows/Linux)

## Results (20% held-out test set)
**Learning type: supervised learning (regression).** See [SYLLABUS_MAPPING.md](SYLLABUS_MAPPING.md)
for how each part of the project maps to Units I-V of the course.

| Model | Family | CV RMSE | Train R² | Test RMSE | Test R² |
|---|---|---|---|---|---|
| SVR (linear kernel) | SVM | 47.32 | 0.919 | 44.12 | 0.929 |
| **Linear Regression** | Linear model | 47.88 | 0.920 | 44.12 | **0.929** |
| Ridge Regression | Linear + L2 | 47.88 | 0.920 | 44.12 | 0.929 |
| Gradient Boosting | Boosting | 55.67 | 0.958 | 59.27 | 0.871 |
| Bagging | Bagging | 69.12 | 0.974 | 69.69 | 0.822 |
| Random Forest | Bagging | 69.22 | 0.975 | 70.26 | 0.819 |
| AdaBoost | Boosting | 76.08 | 0.904 | 80.42 | 0.763 |
| KNN | Instance-based | 82.71 | 1.000 | 74.22 | 0.798 |
| Decision Tree | Tree | 98.43 | 0.873 | 94.68 | 0.672 |

Models are compared on 5-fold cross-validation RMSE on the training split; the test set is used only for the final report. SVR, Linear and Ridge Regression are within one standard error of each other, so the one-standard-error rule picks the simplest: Linear Regression.
