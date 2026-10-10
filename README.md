# PC Performance Predictor (Team 7)

An end-to-end Machine Learning and hardware simulation system that lets users configure a desktop PC from real, modern components (CPU, motherboard, RAM, storage, GPU, cooler, case, power supply, and operating system) and predicts the overall **Performance Score** (scale 0–1000) using a trained supervised regression model. The project also features real-time hardware compatibility validation, thermal and power estimation, rule-based in-game FPS projections across 12 modern titles, professional Excel report generation, and an ASUS laptop companion automation tool (**Armoury Auto**).

---

## Table of Contents
- [Project Overview](#project-overview)
- [Repository Structure](#repository-structure)
- [Dataset & Data Preprocessing](#dataset--data-preprocessing)
- [Machine Learning Architecture & Results](#machine-learning-architecture--results)
- [Hardware Catalog & Compatibility Engine](#hardware-catalog--compatibility-engine)
- [Thermal, Power & FPS Simulation](#thermal-power--fps-simulation)
- [Interactive Streamlit Application](#interactive-streamlit-application)
- [Armoury Auto (Companion Utility)](#armoury-auto-companion-utility)
- [Academic Syllabus Mapping](#academic-syllabus-mapping)
- [Installation & How to Run](#installation--how-to-run)

---

## Project Overview

- **Core Objective**: Predict PC benchmark performance (`Performance_Score`: 0–1000) from hardware specifications using supervised machine learning regression.
- **Key Capabilities**:
  - **Machine Learning**: 9 candidate regression algorithms trained and evaluated using 5-fold cross-validation; simplest model selected via the **One-Standard-Error Rule** (Occam's razor).
  - **Cascading Component Selection**: Choosing a CPU automatically filters motherboards by socket and coolers by heat dissipation; selecting a motherboard filters compatible RAM types (DDR4 vs DDR5) and cases by form factor.
  - **Compatibility Engine**: Validates CPU sockets, RAM generations and slot limits, cooler TDP adequacy, case physical clearances, power supply wattage headroom, and video output requirements.
  - **Physics & Estimation**: Simulates thermal loads based on CPU power draw, cooler dissipation, case airflow, extra fans, and GPU ambient heat. Calculates peak system power draw.
  - **Gaming FPS Projections**: Projects native resolution frame rates (1080p, 1440p, 4K at High settings) across 12 games taking into account CPU/GPU bottlenecks, memory constraints, and thermal throttling.
  - **Reporting**: Exports detailed multi-sheet `.xlsx` build workbooks with formulas, specifications, and performance metrics.
  - **Hardware Companion**: Includes `armoury_auto`, a Windows system tray utility for ASUS TUF gaming laptops to dynamically balance performance and GPU modes (Standard vs Eco) using ASUS ACPI and `nvidia-smi`.

---

## Repository Structure

```
PC_Performance_Predictor/
├── .gitignore                              # Git ignore rules for Python bytecode, caches, logs, environments
├── README.md                               # Project documentation
├── SYLLABUS_MAPPING.md                     # Academic mapping to Machine Learning course (241AI005)
├── PC_Performance_Predictor.pptx           # Summary slide deck
├── PC_Performance_Predictor_detailed.pptx  # In-depth technical presentation slide deck
├── requirements.txt                        # Python package dependencies
├── app.py                                  # Interactive Streamlit PC builder and prediction app
│
├── data/                                   # Datasets
│   ├── pc_performance_raw.csv              # Raw synthetic/benchmark dataset (520 rows)
│   └── pc_performance_cleaned.csv          # Preprocessed, validated, and deduplicated dataset (503 rows)
│
├── src/                                    # Core application modules
│   ├── preprocess.py                       # Data cleaning, range validation, and imputation pipeline
│   ├── train.py                            # Model training, hyperparameter tuning (GridSearchCV), and evaluation
│   ├── catalog.py                          # Real PC hardware component database with specifications
│   ├── build.py                            # Compatibility logic, power estimation, and thermal modeling
│   ├── fps.py                             # Rule-based in-game FPS engine for 12 games at 3 resolutions
│   └── export.py                           # Multi-tab styled Excel report builder (.xlsx)
│
├── models/                                 # Serialized model artifacts
│   ├── performance_model.joblib            # Trained production pipeline (StandardScaler + OneHotEncoder + LinearRegression)
│   └── metrics.json                        # Comprehensive metrics, CV scores, feature importances, and hyperparameter sweeps
│
├── reports/figures/                        # Generated evaluation charts
│   ├── model_comparison.png                # Bar chart comparing Test R² across 9 evaluated models
│   ├── actual_vs_predicted.png             # Scatter plot showing actual vs predicted test scores
│   └── feature_importance.png              # Permutation feature importance chart
│
└── armoury_auto/                           # ASUS TUF Gaming companion automation tool
    ├── README.md                           # Documentation for Armoury Auto
    ├── app.py                              # System tray application & background rule engine
    ├── asus_acpi.py                        # ASUS ACPI WMI communication interface
    ├── gpu.py                              # NVIDIA GPU status detection and nvidia-smi process inspection
    ├── config.json                         # User-configurable automation rules and schedule
    └── state.json                          # Persistent state storage
```

---

## Dataset & Data Preprocessing

### Dataset Schema
The dataset maps 8 hardware and environmental features to an overall system performance benchmark:

| Attribute | Data Type | Valid Range | Description |
|---|---|---|---|
| `RAM_GB` | Integer | 4 – 64 GB | Total system RAM |
| `CPU_Cores` | Integer | 2 – 16 cores | Physical CPU cores |
| `GPU_Level` | Integer | 0 – 12 | Relative graphics card tier (0 = Integrated, 12 = Flagship) |
| `Storage_GB` | Integer | 128 – 2048 GB | Total disk storage capacity |
| `Clock_GHz` | Float | 2.0 – 5.0 GHz | Peak CPU clock frequency |
| `Age_Years` | Float | 0.0 – 8.0 yrs | System operational age |
| `Temperature_C` | Float | 40.0 – 90.0 °C | Average operating temperature under load |
| `OS` | Categorical | Windows, Linux | Operating system family |
| **`Performance_Score`** | **Integer (Target)** | **0 – 1000** | **System benchmark score (Target variable)** |
| `Performance_Class` | Categorical (Derived) | Low, Medium, High, Very High | Classification bracket derived from score |

**Class Bins**:
- **Low**: [0, 400)
- **Medium**: [400, 650)
- **High**: [650, 850)
- **Very High**: [850, 1000]

### Preprocessing Pipeline (`src/preprocess.py`)
Raw records undergo a 7-step data cleaning pipeline (`520 raw rows` → `503 clean rows`):
1. **Type Coercion**: Strips string formatting artifacts (such as `"32GB"` and whitespace) and coerces values to numeric types.
2. **OS Categorical Standardization**: Normalizes 11 user entry variations (`"win10"`, `"windows"`, `"ubuntu"`, etc.) into two canonical categories: `Windows` and `Linux`.
3. **Exact Deduplication (Step 1)**: Identifies and removes duplicate records across feature columns (ignoring `Record_ID`).
4. **Domain Boundary Filtering**: Removes non-physical or out-of-domain rows outside established engineering limits (e.g., negative ages, impossible core counts).
5. **Missing Value Imputation**: Imputes missing numeric values with the column **median** (robust to outliers) and categorical values (`OS`) with the **mode**.
6. **Class Label Recalculation**: Recomputes `Performance_Class` based on cleaned numeric `Performance_Score` thresholds to ensure consistency.
7. **Integer Rounding & Final Deduplication**: Rounds integer-discrete features (`RAM_GB`, `CPU_Cores`, `GPU_Level`, `Storage_GB`) and executes a final deduplication pass.

---

## Machine Learning Architecture & Results

### Learning Paradigm
- **Paradigm**: Supervised Learning (Regression)
- **Train/Test Split**: 80% Training (402 samples), 20% Held-Out Testing (101 samples) with fixed seed (`random_state=42`).
- **Feature Pipeline (`ColumnTransformer`)**:
  - `StandardScaler` applied to the 7 numeric features.
  - `OneHotEncoder(handle_unknown="ignore")` applied to the categorical `OS` feature.
  - Enclosed in an end-to-end `Pipeline` so scaling and encoding parameters are learned strictly on training folds to prevent data leakage.
- **Cross-Validation**: 5-Fold Cross-Validation (`KFold(n_splits=5, shuffle=True, random_state=42)`) coupled with `GridSearchCV` for exhaustive hyperparameter optimization.

### Model Comparison Table
9 distinct regression algorithms representing different learning families were trained and evaluated:

| Model | Learning Family | Syllabus Unit | 5-Fold CV RMSE | Train R² | Test MAE | Test RMSE | Test R² |
|---|---|---|---|---|---|---|---|
| **SVR (Linear kernel)** | Support Vector Machine | Unit III | 47.32 ± 6.73 | 0.919 | 33.33 | 44.12 | 0.929 |
| **Linear Regression** | Linear Model | Unit III | **47.88 ± 6.32** | **0.920** | **33.84** | **44.12** | **0.929** |
| **Ridge Regression** | Linear + L2 Regularization | Unit III / V | 47.88 ± 6.32 | 0.920 | 33.85 | 44.12 | 0.929 |
| **Gradient Boosting** | Ensemble: Boosting | Unit V | 55.67 ± 4.52 | 0.958 | 45.29 | 59.27 | 0.871 |
| **Bagging** | Ensemble: Bagging | Unit V | 69.12 ± 4.65 | 0.974 | 53.29 | 69.69 | 0.822 |
| **Random Forest** | Ensemble: Bagging | Unit V | 69.22 ± 4.70 | 0.975 | 53.55 | 70.26 | 0.819 |
| **AdaBoost** | Ensemble: Boosting | Unit V | 76.08 ± 5.52 | 0.904 | 62.48 | 80.42 | 0.763 |
| **KNN** | Instance-Based Learning | Unit II | 82.71 ± 7.39 | 1.000 | 57.31 | 74.22 | 0.798 |
| **Decision Tree** | Tree (Base Learner) | Unit V | 98.43 ± 3.07 | 0.873 | 77.86 | 94.68 | 0.672 |

### Model Selection: The One-Standard-Error Rule (Occam's Razor)
The cross-validation RMSE of **SVR** ($47.32$), **Linear Regression** ($47.88$), and **Ridge Regression** ($47.88$) are statistically indistinguishable within one standard error ($\text{SE} = \frac{6.73}{\sqrt{5}} \approx 3.01$, threshold = $50.33$). In accordance with the **One-Standard-Error Rule** and the principle of **Occam's razor**, the simplest model that generalizes with minimal complexity is chosen: **Linear Regression**.

Linear Regression achieves:
- **Test $R^2$**: `0.929` (explains ~93% of score variance)
- **Test RMSE**: `44.12` points on a 1000-point scale (~4.4% relative error)
- **Test MAE**: `33.84` points
- **No Overfitting**: High alignment between Train $R^2$ (0.920) and Test $R^2$ (0.929). In contrast, KNN overfits heavily (Train $R^2 = 1.000$ vs Test $R^2 = 0.798$).

### Feature Importance (Permutation Analysis)
Permutation importance calculates the drop in test $R^2$ when a feature column is randomly shuffled:
1. **RAM_GB**: `+0.5345` (Highest impact)
2. **CPU_Cores**: `+0.5131`
3. **GPU_Level**: `+0.3672`
4. **Clock_GHz**: `+0.1699`
5. **Age_Years**: `+0.1225`
6. **Temperature_C**: `+0.0326`
7. **Storage_GB**: `+0.0185`
8. **OS**: `+0.0006` (Negligible impact)

### Regularization Analysis (Ridge $\alpha$ Sweep)
Testing $L_2$ regularization penalties from $\alpha = 0.01$ to $\alpha = 10,000$ revealed:
- $\alpha \in [0.01, 1]$ maintains CV RMSE at ~`47.88`.
- Higher values overly constrain coefficients, creating underfitting: $\alpha = 100 \implies \text{RMSE } 60.69$, and $\alpha = 10,000 \implies \text{RMSE } 160.31$.

---

## Hardware Catalog & Compatibility Engine

### Component Database (`src/catalog.py`)
The catalog includes real-world components with physical specifications:
- **46 Processors (CPUs)**: AMD Ryzen 5000, 7000, 8000, 9000 series; Intel Core 12th, 13th, 14th Gen, and Core Ultra. Includes socket types (`AM4`, `AM5`, `LGA1700`, `LGA1851`), core counts, boost clocks, TDP, integrated GPU ratings, and stock cooler flags.
- **33 Motherboards**: Chipsets covering AM4 (B450, B550, X570), AM5 (B650, X670, X870), LGA1700 (B660, B760, Z790), LGA1851 (Z890) across `ATX`, `Micro-ATX`, and `Mini-ITX` form factors, specifying RAM slots and DDR generation.
- **21 RAM Kits**: DDR4 and DDR5 memory kits from 8 GB to 64 GB in single and dual stick configurations.
- **34 Storage Drives**: NVMe PCIe 3.0/4.0/5.0 SSDs and SATA HDDs from 256 GB up to 2 TB.
- **35 Graphics Cards (GPUs)**: AMD Radeon, NVIDIA GeForce (RTX 30 & 40 series), Intel Arc, and integrated graphics options spanning Tier 0 to Tier 12.
- **17 CPU Coolers**: Stock coolers, budget air towers, dual-tower coolers, and 240mm/360mm AIO liquid coolers rated by cooling capacity in Watts.
- **17 PC Cases**: Form-factor compatibility (`ATX`, `Micro-ATX`, `Mini-ITX`) and rated airflow profiles (`High`, `Medium`, `Low`).
- **20 Power Supplies (PSUs)**: 80-Plus rated units ranging from 450 W to 1000 W.
- **Extra Case Fans**: Options to add 0 to 6 auxiliary cooling fans.
- **5 Operating Systems**: Windows 11, Windows 10, Ubuntu, Linux Mint, and Fedora.

### Compatibility Engine (`src/build.py`)
Validates that components function together:
- **Socket Matching**: Prevents pairing incompatible CPU and motherboard sockets (e.g., AM5 CPU in an AM4 board).
- **RAM Compatibility**: Enforces motherboard DDR memory type (DDR4 vs DDR5) and prevents exceeding total physical RAM DIMM slots.
- **Form Factor Clearance**: Ensures motherboards physically fit inside the chosen case (`ATX` motherboards cannot fit in `Mini-ITX` cases).
- **Display Output Validation**: Flags an error if a CPU lacks integrated graphics (`iGPU = False`) and no dedicated GPU is selected.
- **Cooler Requirement**: Disallows selecting "Stock Cooler" if the CPU does not ship with one in the box.
- **Power Capacity Check**: Prevents operating with a PSU whose wattage is lower than total estimated system power draw.
- **Headroom Warnings**: Emits warnings if PSU wattage is within 30% of peak draw ($1.3\times$ safety margin recommended) or if cooler capacity is insufficient for CPU heat.

---

## Thermal, Power & FPS Simulation

### Power Draw Estimation
Calculated as:
$$\text{Power Draw (W)} = \text{CPU Power (W)} + \text{GPU Power (W)} + 75\text{ W (Base System: motherboard, RAM, drives, fans)}$$
Recommended PSU wattage is dynamically rounded up with a $30\%$ safety margin (minimum 450 W).

### Operating Temperature Simulation
Estimated CPU temperature under full load incorporates cooler dissipation efficiency, case airflow characteristics, and thermal dumping from the GPU:
$$\text{Temp (°C)} = 38 + 35 \times \left(\frac{\text{CPU Power}}{\text{Cooler Capacity}}\right) + \text{Airflow Penalty} + \left(\frac{\text{GPU Power}}{60}\right) - \text{Fan Cooling Benefit}$$
- **Airflow Penalty**: High Airflow: $+0\text{°C}$, Medium Airflow: $+4\text{°C}$, Low Airflow: $+9\text{°C}$.
- **Fan Cooling Curve**: Extra fans grant diminishing returns (from $0\text{°C}$ for 0 fans up to $5.0\text{°C}$ for 6 fans).
- Output is bounded within realistic operating ranges [$40.0\text{°C}$, $95.0\text{°C}$].

### In-Game FPS Projections (`src/fps.py`)
Predicts native rendering performance at **1080p**, **1440p**, and **4K** (High settings) across 12 demanding and popular games:
- *Cyberpunk 2077, Black Myth: Wukong, Red Dead Redemption 2, Hogwarts Legacy, Elden Ring, Call of Duty: Warzone, Fortnite, Apex Legends, GTA V, Counter-Strike 2, Valorant, Minecraft (Java)*.

**Calculation Formula**:
$$\text{GPU FPS} = \text{Reference FPS}_{\text{GPU}} \times \frac{\text{GPU Index}}{100}$$
$$\text{CPU FPS} = \text{Reference FPS}_{\text{CPU}} \times \frac{\text{CPU Gaming Index}}{100}$$
$$\text{Base FPS} = \left( \text{GPU FPS}^{-4} + \text{CPU FPS}^{-4} \right)^{-1/4}$$
- **Soft Minimum**: Smoothly accounts for both GPU and CPU bottlenecks using a power-4 harmonic mean.
- **RAM Penalty**: Applies a $0.6\times$ penalty if system RAM $< 8\text{ GB}$, and $0.85\times$ if $< 16\text{ GB}$.
- **Thermal Throttling**: Reduces performance by $3\%$ if temperatures reach $\ge 80\text{°C}$, and $7\%$ if $\ge 88\text{°C}$.
- **Engine FPS Caps**: Caps results for games with hardcoded engine limits (Elden Ring: 60 FPS, Apex Legends: 300 FPS, GTA V: 187 FPS).

### Excel Report Export (`src/export.py`)
Generates a downloadable, professionally formatted `.xlsx` workbook with four dedicated sheets:
1. **Summary**: System score, tier, error margins, compatibility verification, power draw, and temperature.
2. **Parts**: Selected components and technical specifications.
3. **Game FPS**: Multi-resolution gaming performance table with playability ratings (Smooth 60+, Playable 30-59, Low <30).
4. **Model Inputs**: The exact 8 values passed into the scikit-learn regression pipeline.

---

## Interactive Streamlit Application

The interactive web builder (`app.py`) provides:
- **Interactive Builder Sidebar**: Displays real-time model metrics ($R^2$, MAE, RMSE) and live component counts.
- **Dynamic Dependency Filtering**: Dropdowns dynamically filter downstream components in real time.
- **Real-Time Score Delta**: Computes score adjustments instantly upon changing parts (e.g., `+42 from last change`).
- **Live Visual Metrics**: Includes a color-coded performance meter, power load bar, and temperature readouts.
- **Compatibility Alerts**: Clear error banners for mismatched parts and warnings for tight thermal/power headroom.
- **Three Data Tabs**:
  - **Game FPS Tab**: Interactive resolution selector (1080p / 1440p / 4K) with progress bars, median FPS, and count of 60+ FPS games.
  - **Parts List Tab**: Formatted parts table.
  - **What the Model Sees Tab**: Direct breakdown of how hardware choices were transformed into model inputs.
- **One-Click Excel Download**: Instantly exports the configured build report.

---

## Armoury Auto (Companion Utility)

Located in `armoury_auto/`, this background utility is designed for ASUS gaming laptops (tested on ASUS TUF Gaming A16 / RTX 5070):
- **Automated Performance & GPU Modes**: Automatically adjusts performance profiles (**Silent**, **Performance**, **Turbo**) and GPU states (**Eco** / **Standard**) based on AC power status, battery level, CPU/GPU utilization, idle state, and time schedules.
- **ASUS ACPI Driver Integration (`asus_acpi.py`)**: Interacts directly with ASUS ACPI WMI calls (the same driver used by the `Fn + F5` hotkey) without requiring third-party bloatware.
- **GPU Safety Inspection (`gpu.py`)**: Uses `nvidia-smi` to inspect active GPU processes before switching to Eco mode, preventing abrupt crashes if a game or CAD application is running.
- **System Tray Controls**: Right-click tray menu to force GPU modes, pause automation, lock specific profiles, or edit rules in `config.json`.

---

## Academic Syllabus Mapping

This project was built to satisfy the requirements of the academic course **Machine Learning (Course Code: 241AI005)**. Every technique maps directly to Units I–V:

| Unit | Course Syllabus Topic | Implementation in this Project |
|---|---|---|
| **Unit I** | Types of ML Systems & Data Challenges | Supervised batch regression learning; handling dirty, missing, duplicate, and out-of-range benchmark data (`src/preprocess.py`). |
| **Unit II** | Instance-Based Learning & Metrics | $k$-Nearest Neighbors regression (`KNN`) evaluated with $k \in \{3, 5, 7, 11\}$, uniform vs. distance weighting, Euclidean vs. Manhattan metrics. |
| **Unit II** | Bayesian Learning & Maximum Likelihood | Ordinary Least Squares in Linear Regression is the Maximum Likelihood Estimate under Gaussian error assumptions. |
| **Unit III** | Linear Regression & Support Vector Machines | Linear Regression (selected final model: Test $R^2 = 0.929$); SVR tested with linear and non-linear RBF kernels with $C$ and $\epsilon$ parameter sweeps. |
| **Unit IV** | Hypothesis Evaluation & Cross-Validation | 80/20 train/test splitting; 5-fold cross-validation with `GridSearchCV`; evaluation using MAE, MSE, RMSE, and $R^2$. |
| **Unit IV** | Feature Encoding & Bias-Variance Analysis | Categorical one-hot encoding within leak-proof pipelines; analysis of train vs. test metrics to diagnose bias and variance. |
| **Unit V** | Ensemble Learning | Implementation and comparison of **Bagging**, **Random Forest**, **Gradient Boosting**, and **AdaBoost** regressors. |
| **Unit V** | Regularization & Generalization | Ridge ($L_2$) regularization penalty sweep ($\alpha \in [0.01, 10000]$); selection via Occam's razor and the One-Standard-Error rule. |

*Note: Unsupervised clustering (k-Means, DBSCAN) and classification algorithms (Logistic Regression, Naive Bayes) are deliberately omitted as the problem is strictly a supervised numeric regression task.*

---

## Installation & How to Run

### Prerequisites
- Python 3.10+ (tested on Python 3.12 / 3.14)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Sashankdeva/PC_Performance_Predictor.git
cd PC_Performance_Predictor
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Preprocess Dataset (Optional - clean CSV is pre-generated)
```bash
python src/preprocess.py
```
*Output: Cleans `data/pc_performance_raw.csv` and produces `data/pc_performance_cleaned.csv` (503 valid rows).*

### 4. Train and Evaluate Models (Optional - model is pre-trained)
```bash
python src/train.py
```
*Output: Runs 5-fold CV across 9 models, updates `models/metrics.json`, serializes `models/performance_model.joblib`, and outputs charts to `reports/figures/`.*

### 5. Launch the Streamlit Application
```bash
streamlit run app.py
```
The app will open automatically in your browser at `http://localhost:8501`.

### 6. Run Armoury Auto (Optional - ASUS Laptop Utility)
```bash
# Run in background system tray:
pythonw armoury_auto/app.py

# Check current rule match and battery status:
python armoury_auto/app.py --status

# Dry-run logging decisions without switching profiles:
python armoury_auto/app.py --dry-run
```
