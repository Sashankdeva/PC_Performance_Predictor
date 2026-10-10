from pathlib import Path
# pyrefly: ignore [missing-import]
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "pc_performance_raw.csv"
CLEAN_PATH = ROOT / "data" / "pc_performance_cleaned.csv"

NUMERIC_COLS = ["RAM_GB", "CPU_Cores", "GPU_Level", "Storage_GB",
                "Clock_GHz", "Age_Years", "Temperature_C", "Performance_Score"]
INTEGER_COLS = ["RAM_GB", "CPU_Cores", "GPU_Level", "Storage_GB"]

VALID_RANGES = {
    "RAM_GB": (4, 64),
    "CPU_Cores": (2, 16),
    "GPU_Level": (0, 12),
    "Storage_GB": (128, 2048),
    "Clock_GHz": (2.0, 5.0),
    "Age_Years": (0, 8),
    "Temperature_C": (40, 90),
    "Performance_Score": (0, 1000),
}

# Map all OS spelling variations to two standard categories
OS_MAP = {
    "windows": "Windows", "windows 10": "Windows", "win10": "Windows",
    "linux": "Linux", "ubuntu": "Linux",
}

CLASS_BINS = [-np.inf, 400, 650, 850, np.inf]
CLASS_LABELS = ["Low", "Medium", "High", "Very High"]


def score_to_class(score):
    return pd.cut(np.atleast_1d(score), bins=CLASS_BINS, labels=CLASS_LABELS,
                  right=False).astype(str)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Step 1 — Fix data types: strip "GB" suffix and whitespace, coerce to numeric
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace("GB", "", case=False).str.strip(),
            errors="coerce")

    # Step 2 — Standardize OS labels (11 variations → 2 categories)
    df["OS"] = df["OS"].str.strip().str.lower().map(OS_MAP)

    # Step 3 — Remove exact duplicate rows (ignoring Record_ID)
    feature_cols = [c for c in df.columns if c != "Record_ID"]
    df = df.drop_duplicates(subset=feature_cols)

    # Step 4 — Drop rows with values outside valid engineering ranges
    valid = pd.Series(True, index=df.index)
    for col, (lo, hi) in VALID_RANGES.items():
        valid &= df[col].isna() | df[col].between(lo, hi)
    df = df[valid]

    # Step 5 — Impute missing values: median for numbers, mode for OS
    for col in NUMERIC_COLS:
        df[col] = df[col].fillna(df[col].median())
    df["OS"] = df["OS"].fillna(df["OS"].mode()[0])

    # Step 6 — Recompute Performance_Class from the cleaned score
    df["Performance_Class"] = score_to_class(df["Performance_Score"])

    # Step 7 — Round integer columns and remove any new duplicates
    df[INTEGER_COLS] = df[INTEGER_COLS].round().astype(int)
    df = df.drop_duplicates(subset=feature_cols).reset_index(drop=True)
    df["Record_ID"] = np.arange(1, len(df) + 1)
    return df


def main():
    raw = pd.read_csv(RAW_PATH)
    cleaned = clean(raw)
    cleaned.to_csv(CLEAN_PATH, index=False)
    print(f"Raw rows: {len(raw)} -> clean rows: {len(cleaned)}")
    print(f"Missing values: {int(cleaned.isna().sum().sum())}")
    print(f"OS categories: {sorted(cleaned['OS'].unique())}")
    print(f"Score range: {cleaned['Performance_Score'].min()} - "
          f"{cleaned['Performance_Score'].max()}")
    print(f"Saved to {CLEAN_PATH}")


if __name__ == "__main__":
    main()
