"""
Variability analysis: learning curves, day-position effects, outliers, variance decomposition.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from data_loading import (
    load_and_clean, get_clean_subset, get_standard_pvi,
    STEP_COLS, RESULTS_DIR, FIGURES_DIR,
)

plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "font.size": 10})

PALETTE = {"Dr. A": "#2196F3", "Dr. B": "#FF9800", "Dr. C": "#4CAF50"}


def plot_learning_curves(df):
    """CASE_TIME vs physician case sequence number — learning effect."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for ax, col, title in zip(axes,
        ["CASE_TIME", "SKIN_SKIN", "PT_IN_OUT"],
        ["Case Time", "Skin-to-Skin", "Patient In-Out"]):
        for phys in ["Dr. A", "Dr. B", "Dr. C"]:
            sub = df[df["PHYSICIAN"] == phys].sort_values("PHYSICIAN_CASE_SEQ")
            ax.scatter(sub["PHYSICIAN_CASE_SEQ"], sub[col], alpha=0.4,
                       color=PALETTE[phys], label=phys, s=20)
            # Rolling average (window=10)
            if len(sub) >= 10:
                rolling = sub[col].rolling(10, min_periods=5).mean()
                ax.plot(sub["PHYSICIAN_CASE_SEQ"], rolling, color=PALETTE[phys], lw=2)
        ax.set_xlabel("Physician's Case # (Sequential)")
        ax.set_ylabel("Minutes")
        ax.set_title(title, fontsize=11)
        ax.legend()

    plt.suptitle("Learning Curves by Physician (dots + 10-case rolling average)", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "learning_curves.png")
    plt.close()
    print("Saved: learning_curves.png")


def plot_learning_curve_steps(df_std):
    """Learning curves for individual steps (standard PVI only)."""
    steps = ["PT_PREP", "TSP", "PRE_MAP", "ABL_DURATION"]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for ax, col in zip(axes, steps):
        for phys in ["Dr. A", "Dr. B", "Dr. C"]:
            sub = df_std[df_std["PHYSICIAN"] == phys].sort_values("PHYSICIAN_CASE_SEQ")
            ax.scatter(sub["PHYSICIAN_CASE_SEQ"], sub[col], alpha=0.3,
                       color=PALETTE[phys], s=15, label=phys)
            if len(sub) >= 8:
                rolling = sub[col].rolling(8, min_periods=4).mean()
                ax.plot(sub["PHYSICIAN_CASE_SEQ"], rolling, color=PALETTE[phys], lw=2)
        ax.set_title(col.replace("_", " "), fontsize=11)
        ax.set_xlabel("Physician Case #")
        ax.set_ylabel("Minutes")
        ax.legend(fontsize=8)

    plt.suptitle("Step-Level Learning Curves (Standard PVI Only)", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "learning_curves_steps.png")
    plt.close()
    print("Saved: learning_curves_steps.png")


def plot_day_position_effect(df):
    """Do cases later in the day take more or less time?"""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Case time by day position
    ax = axes[0]
    for phys in ["Dr. A", "Dr. B", "Dr. C"]:
        sub = df[df["PHYSICIAN"] == phys]
        means = sub.groupby("DAY_POSITION")["CASE_TIME"].mean()
        ax.plot(means.index, means.values, "o-", color=PALETTE[phys], label=phys)
    ax.set_xlabel("Case Position in Day (1=first, 2=second, ...)")
    ax.set_ylabel("Mean Case Time (min)")
    ax.set_title("Case Time by Position in Day", fontsize=11)
    ax.legend()

    # Boxplot of case time by day position
    ax = axes[1]
    df_pos = df[df["DAY_POSITION"] <= 6].copy()
    sns.boxplot(data=df_pos, x="DAY_POSITION", y="CASE_TIME", ax=ax,
                hue="DAY_POSITION", palette="YlOrRd", legend=False)
    ax.set_xlabel("Case Position in Day")
    ax.set_ylabel("Case Time (min)")
    ax.set_title("Case Time Distribution by Day Position", fontsize=11)

    plt.suptitle("Day-of-Schedule Effects", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "day_position_effect.png")
    plt.close()
    print("Saved: day_position_effect.png")

    # Summary stats
    pos_stats = df.groupby("DAY_POSITION")[["CASE_TIME", "PT_IN_OUT"]].agg(["mean", "median", "std", "count"])
    pos_stats.to_csv(RESULTS_DIR / "day_position_stats.csv", float_format="%.1f")
    print("\n=== Day Position Stats ===")
    print(pos_stats.round(1).to_string())


def plot_cases_per_day_effect(df):
    """Does scheduling more cases per day affect performance?"""
    fig, ax = plt.subplots(figsize=(8, 5))
    for phys in ["Dr. A", "Dr. B", "Dr. C"]:
        sub = df[df["PHYSICIAN"] == phys]
        means = sub.groupby("CASES_PER_DAY")["CASE_TIME"].mean()
        ax.plot(means.index, means.values, "o-", color=PALETTE[phys], label=phys, markersize=8)
    ax.set_xlabel("Number of Cases Scheduled That Day")
    ax.set_ylabel("Mean Case Time (min)")
    ax.set_title("Impact of Daily Caseload on Case Time", fontsize=12)
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "cases_per_day_effect.png")
    plt.close()
    print("Saved: cases_per_day_effect.png")


def identify_outliers(df):
    """Flag and display outliers based on IQR for CASE_TIME."""
    q1 = df["CASE_TIME"].quantile(0.25)
    q3 = df["CASE_TIME"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outliers = df[(df["CASE_TIME"] < lower) | (df["CASE_TIME"] > upper)].copy()
    outliers = outliers[["CASE_NUM", "PHYSICIAN", "CASE_TIME", "PT_IN_OUT", "TSP",
                          "PRE_MAP", "ABL_DURATION", "NOTE", "STANDARD_PVI"]].sort_values("CASE_TIME", ascending=False)

    outliers.to_csv(RESULTS_DIR / "outliers.csv", index=False, float_format="%.1f")
    print(f"\n=== CASE_TIME Outliers (IQR method, bounds: [{lower:.0f}, {upper:.0f}]) ===")
    print(f"Found {len(outliers)} outliers:")
    print(outliers.to_string(index=False))
    return outliers


def variance_decomposition(df_std):
    """How much does each step contribute to the variance of CASE_TIME?"""
    # CASE_TIME ≈ ACCESS + TSP + PRE_MAP + ABL_DURATION (roughly, some steps overlap)
    # We'll look at the variance of each step relative to total
    steps = ["ACCESS", "TSP", "PRE_MAP", "ABL_DURATION"]
    variances = df_std[steps].var()
    covariance_matrix = df_std[steps].cov()

    total_var = df_std["CASE_TIME"].var()
    pct_var = (variances / total_var * 100).round(1)

    result = pd.DataFrame({
        "Variance (min²)": variances.round(1),
        "% of CASE_TIME Variance": pct_var,
        "Std Dev (min)": df_std[steps].std().round(1),
    })
    result.to_csv(RESULTS_DIR / "variance_decomposition.csv")
    print("\n=== Variance Decomposition (Standard PVI) ===")
    print(f"Total CASE_TIME variance: {total_var:.1f} min²")
    print(result.to_string())

    # Visualization
    fig, ax = plt.subplots(figsize=(8, 5))
    pct_var.plot(kind="bar", ax=ax, color="steelblue", edgecolor="black")
    ax.set_title("Variance Contribution to Case Time (Standard PVI)", fontsize=12)
    ax.set_ylabel("% of CASE_TIME Variance")
    ax.set_xlabel("")
    for i, v in enumerate(pct_var):
        ax.text(i, v + 0.5, f"{v:.0f}%", ha="center", fontsize=10)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "variance_decomposition.png")
    plt.close()
    print("Saved: variance_decomposition.png")

    return result


def plot_timeline(df):
    """CASE_TIME over calendar time, showing all physicians."""
    fig, ax = plt.subplots(figsize=(14, 5))
    for phys in ["Dr. A", "Dr. B", "Dr. C"]:
        sub = df[df["PHYSICIAN"] == phys].sort_values("DATE")
        ax.scatter(sub["DATE"], sub["CASE_TIME"], color=PALETTE[phys],
                   alpha=0.5, s=25, label=phys)
        # Monthly rolling average
        monthly = sub.set_index("DATE")["CASE_TIME"].resample("2W").mean().dropna()
        if len(monthly) > 1:
            ax.plot(monthly.index, monthly.values, color=PALETTE[phys], lw=2)
    ax.set_xlabel("Date")
    ax.set_ylabel("Case Time (min)")
    ax.set_title("Case Time Over Calendar Time (bi-weekly rolling average)", fontsize=12)
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "case_time_timeline.png")
    plt.close()
    print("Saved: case_time_timeline.png")


def run_variability_analysis():
    df = load_and_clean()
    clean = get_clean_subset(df)
    std = get_standard_pvi(df)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PHASE 2b: VARIABILITY & LEARNING CURVE ANALYSIS")
    print("=" * 60)

    plot_learning_curves(clean)
    plot_learning_curve_steps(std)
    plot_day_position_effect(clean)
    plot_cases_per_day_effect(clean)
    identify_outliers(clean)
    variance_decomposition(std)
    plot_timeline(clean)

    print("\n" + "=" * 60)
    print("VARIABILITY ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_variability_analysis()
