"""
Data loading and cleaning for MSE 433 Module 4 — EP Lab procedure analysis.
"""
import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "MSE433_M4_Data.xlsx"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

STEP_COLS = [
    "PT_PREP", "ACCESS", "TSP", "PRE_MAP",
    "ABL_DURATION", "ABL_TIME", "LA_DWELL",
    "POST_CARE"
]

DURATION_COLS = STEP_COLS + ["CASE_TIME", "SKIN_SKIN", "PT_IN_OUT"]


def load_and_clean():
    """Load the Excel file, rename columns, clean data, return a clean DataFrame."""
    # Raw layout: row 0-1 = banner/title, row 2 = column names, row 3 = units, data from row 4
    df = pd.read_excel(DATA_PATH, sheet_name="All Data", header=None, skiprows=[0, 1, 3])

    # Row 2 (now row 0) has column names — set them and drop that row
    col_names = df.iloc[0].tolist()
    df = df.iloc[1:].reset_index(drop=True)
    df.columns = col_names

    # Drop leading unnamed column
    df = df.loc[:, df.columns.notna()]

    rename_map = {
        "CASE #": "CASE_NUM",
        "DATE": "DATE",
        "PHYSICIAN": "PHYSICIAN",
        "PT PREP/INTUBATION": "PT_PREP",
        "ACCESSS": "ACCESS",
        "TSP": "TSP",
        "PRE-MAP": "PRE_MAP",
        "ABL DURATION": "ABL_DURATION",
        "ABL TIME": "ABL_TIME",
        "#ABL": "NUM_ABL",
        "#APPLICATIONS": "NUM_APPLICATIONS",
        "LA DWELL TIME": "LA_DWELL",
        "CASE TIME": "CASE_TIME",
        "AVG CASE TIME": "AVG_CASE_TIME",
        "SKIN-SKIN": "SKIN_SKIN",
        "AVG SKIN-SKIN": "AVG_SKIN_SKIN",
        "POST CARE/EXTUBATION": "POST_CARE",
        "AVG TURNOVER TIME": "AVG_TURNOVER",
        "PT OUT TIME": "PT_OUT_TIME",
        "PT IN-OUT": "PT_IN_OUT",
        "Note": "NOTE",
    }
    df = df.rename(columns=rename_map)
    known = set(rename_map.values())
    df = df[[c for c in df.columns if c in known]]

    # Coerce numeric columns
    numeric_cols = [
        "CASE_NUM", "PT_PREP", "ACCESS", "TSP", "PRE_MAP",
        "ABL_DURATION", "ABL_TIME", "NUM_ABL", "NUM_APPLICATIONS",
        "LA_DWELL", "CASE_TIME", "AVG_CASE_TIME", "SKIN_SKIN",
        "AVG_SKIN_SKIN", "POST_CARE", "AVG_TURNOVER", "PT_IN_OUT"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Parse DATE — fix known typo "Juy 21" → "2025-07-21"
    df["DATE"] = df["DATE"].astype(str).str.replace("Juy 21", "2025-07-21", regex=False)
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    # Clean PHYSICIAN
    df["PHYSICIAN"] = df["PHYSICIAN"].astype(str).str.strip()

    # Clean NOTE
    if "NOTE" in df.columns:
        df["NOTE"] = df["NOTE"].fillna("").astype(str).str.strip()
    else:
        df["NOTE"] = ""

    # Flag rows with missing core data
    df["HAS_DATA"] = df["CASE_TIME"].notna()

    # Flag non-standard PVI cases (additional ablation targets)
    extra_targets = ["CTI", "BOX", "PST BOX", "SVC", "AAFL"]
    df["EXTRA_TARGETS"] = df["NOTE"].apply(
        lambda n: any(t in str(n).upper() for t in extra_targets)
    )
    df["TROUBLESHOOT"] = df["NOTE"].str.upper().str.contains("TROUBLESHOOT", na=False)
    df["STANDARD_PVI"] = ~df["EXTRA_TARGETS"] & ~df["TROUBLESHOOT"] & df["HAS_DATA"]

    # Case sequence per physician (for learning curve)
    df_valid = df[df["HAS_DATA"]].copy()
    df_valid["PHYSICIAN_CASE_SEQ"] = df_valid.groupby("PHYSICIAN").cumcount() + 1
    df = df.merge(
        df_valid[["CASE_NUM", "PHYSICIAN_CASE_SEQ"]],
        on="CASE_NUM", how="left"
    )

    # Day position: case order within the same date
    df_valid = df[df["HAS_DATA"]].copy()
    df_valid["DAY_POSITION"] = df_valid.groupby("DATE").cumcount() + 1
    df_valid["CASES_PER_DAY"] = df_valid.groupby("DATE")["CASE_NUM"].transform("count")
    df = df.merge(
        df_valid[["CASE_NUM", "DAY_POSITION", "CASES_PER_DAY"]],
        on="CASE_NUM", how="left"
    )

    return df


def get_clean_subset(df):
    """Return only rows with complete data."""
    return df[df["HAS_DATA"]].copy()


def get_standard_pvi(df):
    """Return only standard PVI cases (no extra targets, no troubleshoot, has data)."""
    return df[df["STANDARD_PVI"]].copy()


if __name__ == "__main__":
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = load_and_clean()
    clean = get_clean_subset(df)
    std = get_standard_pvi(df)

    print(f"Total rows: {len(df)}")
    print(f"Rows with data: {len(clean)}")
    print(f"Standard PVI cases: {len(std)}")
    print(f"Cases with extra targets: {df['EXTRA_TARGETS'].sum()}")
    print(f"Troubleshoot cases: {df['TROUBLESHOOT'].sum()}")
    print(f"\nPhysician counts (with data):")
    print(clean["PHYSICIAN"].value_counts().to_string())
    print(f"\nDate range: {clean['DATE'].min().date()} to {clean['DATE'].max().date()}")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nSample:\n{clean[['CASE_NUM','PHYSICIAN','CASE_TIME','PT_IN_OUT','NOTE']].head(10).to_string()}")
