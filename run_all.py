#!/usr/bin/env python3
"""
MSE 433 Module 4 — EP Lab Efficiency Analysis
Run all analysis phases: EDA, Variability, Statistical Modeling.

Usage:
    python3 run_all.py
"""
import sys
from pathlib import Path

# Ensure src/ is on the path
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from data_loading import load_and_clean, get_clean_subset, get_standard_pvi, RESULTS_DIR, FIGURES_DIR
from eda import run_eda
from variability_analysis import run_variability_analysis
from statistical_modeling import run_statistical_modeling


def main():
    # Ensure output directories exist
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("MSE 433 MODULE 4 — EP LAB EFFICIENCY ANALYSIS")
    print("=" * 70)

    # Verify data loads
    df = load_and_clean()
    clean = get_clean_subset(df)
    std = get_standard_pvi(df)
    print(f"\nData loaded: {len(df)} total, {len(clean)} with data, {len(std)} standard PVI")
    print(f"Physicians: {clean['PHYSICIAN'].value_counts().to_dict()}")
    print(f"Date range: {clean['DATE'].min().date()} to {clean['DATE'].max().date()}")

    # Run all phases
    print("\n")
    run_eda()

    print("\n")
    run_variability_analysis()

    print("\n")
    run_statistical_modeling()

    # Summary of outputs
    print("\n" + "=" * 70)
    print("ALL ANALYSES COMPLETE")
    print("=" * 70)
    print(f"\nResults directory: {RESULTS_DIR}")
    print("\nCSV files generated:")
    for f in sorted(RESULTS_DIR.glob("*.csv")):
        print(f"  - {f.name}")
    print("\nFigures generated:")
    for f in sorted(FIGURES_DIR.glob("*.png")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()
