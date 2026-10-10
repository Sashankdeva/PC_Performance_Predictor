"""Clean the raw PC performance dataset into a machine-learning-ready CSV.

Steps (as described in Review-1):
  1. Fix data types (e.g. RAM_GB values like " 32GB")
  2. Standardize OS labels to Windows / Linux
  3. Remove exact duplicates (ignoring Record_ID)
  4. Filter impossible / out-of-range values
  5. Impute missing numbers with the median and OS with the mode
  6. Recompute Performance_Class from Performance_Score
  7. Round integer-valued columns and remove duplicates again
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "pc_performance_raw.csv"
CLEAN_PATH = ROOT / "data" / "pc_performance_cleaned.csv"

NUMERIC_COLS = ["RAM_GB", "CPU_Cores", "GPU_Level", "Storage_GB",
                "Clock_GHz", "Age_Years", "Temperature_C", "Performance_Score"]
INTEGER_COLS = ["RAM_GB", "CPU_Cores", "GPU_Level", "Storage_GB"]

# Valid domain limits (inclusive)
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

OS_MAP = {
    "windows": "Windows", "windows 10": "Windows", "win10": "Windows",
    "linux": "Linux", "ubuntu": "Linux",
}

# Score thresholds for each class: [lower, upper)
CLASS_BINS = [-np.inf, 400, 650, 850, np.inf]
CLASS_LABELS = ["Low", "Medium", "High", "Very High"]


def score_to_class(score):
    """Map a performance score (scalar or Series) to its performance class."""
    return pd.cut(np.atleast_1d(score), bins=CLASS_BINS, labels=CLASS_LABELS,
                  right=False).astype(str)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Data types: strip "GB" suffix / whitespace and coerce to numbers
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace("GB", "", case=False).str.strip(),
            errors="coerce")

    # 2. Standardize OS labels
    df["OS"] = df["OS"].str.strip().str.lower().map(OS_MAP)

    # 3. Remove exact duplicates, ignoring Record_ID
    feature_cols = [c for c in df.columns if c != "Record_ID"]
    df = df.drop_duplicates(subset=feature_cols)

    # 4. Drop rows with impossible values (missing values are kept for imputation)
    valid = pd.Series(True, index=df.index)
    for col, (lo, hi) in VALID_RANGES.items():
        valid &= df[col].isna() | df[col].between(lo, hi)
    df = df[valid]

    # 5. Impute missing values
    for col in NUMERIC_COLS:
        df[col] = df[col].fillna(df[col].median())
    df["OS"] = df["OS"].fillna(df["OS"].mode()[0])

    # 6. Recompute the class label from the cleaned score
    df["Performance_Class"] = score_to_class(df["Performance_Score"])

    # 7. Round integer columns and remove duplicates again
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
