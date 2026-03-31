"""
EDA: Descriptive statistics, distributions, and physician comparisons.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from data_loading import (
    load_and_clean, get_clean_subset, get_standard_pvi,
    STEP_COLS, DURATION_COLS, RESULTS_DIR, FIGURES_DIR,
)

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 10,
})


def summary_statistics(df):
    """Overall and per-physician summary stats for all duration columns."""
    cols = [c for c in DURATION_COLS if c in df.columns]

    overall = df[cols].describe().T
    overall["cv"] = overall["std"] / overall["mean"]
    overall["iqr"] = overall["75%"] - overall["25%"]
    overall.to_csv(RESULTS_DIR / "summary_stats_overall.csv", float_format="%.2f")
    print("\n=== Overall Summary Stats ===")
    print(overall[["count", "mean", "std", "cv", "min", "25%", "50%", "75%", "max"]].to_string())

    by_phys = []
    for phys, grp in df.groupby("PHYSICIAN"):
        stats = grp[cols].describe().T
        stats["cv"] = stats["std"] / stats["mean"]
        stats["PHYSICIAN"] = phys
        by_phys.append(stats)
    by_phys = pd.concat(by_phys)
    by_phys.to_csv(RESULTS_DIR / "summary_stats_by_physician.csv", float_format="%.2f")
    print("\n=== By Physician (mean) ===")
    pivot = df.groupby("PHYSICIAN")[cols].mean().T
    print(pivot.round(1).to_string())

    return overall, by_phys


def plot_distributions(df):
    """Histograms for each procedure step."""
    cols = STEP_COLS
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    axes = axes.flatten()
    for i, col in enumerate(cols):
        if col in df.columns:
            ax = axes[i]
            df[col].dropna().hist(ax=ax, bins=20, edgecolor="black", alpha=0.7)
            ax.set_title(col.replace("_", " "), fontsize=11)
            ax.set_xlabel("Minutes")
            ax.axvline(df[col].median(), color="red", ls="--", label=f"Median={df[col].median():.0f}")
            ax.legend(fontsize=8)
    plt.suptitle("Distribution of Procedure Step Durations (All Cases with Data)", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "step_distributions.png")
    plt.close()
    print("Saved: step_distributions.png")


def plot_total_distributions(df):
    """Histograms for CASE_TIME and PT_IN_OUT."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, col, title in zip(axes,
        ["CASE_TIME", "SKIN_SKIN", "PT_IN_OUT"],
        ["Case Time (Cath In–Out)", "Skin-to-Skin (Access–Cath Out)", "Patient In–Out (Total)"]):
        data = df[col].dropna()
        ax.hist(data, bins=20, edgecolor="black", alpha=0.7, color="steelblue")
        ax.axvline(data.median(), color="red", ls="--", label=f"Median={data.median():.0f}")
        ax.axvline(data.mean(), color="orange", ls="--", label=f"Mean={data.mean():.0f}")
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Minutes")
        ax.legend(fontsize=8)
    plt.suptitle("Distribution of Total Durations", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "total_duration_distributions.png")
    plt.close()
    print("Saved: total_duration_distributions.png")


def plot_boxplots_by_physician(df):
    """Box plots per procedure step, colored by physician."""
    cols = STEP_COLS
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    axes = axes.flatten()
    palette = {"Dr. A": "#2196F3", "Dr. B": "#FF9800", "Dr. C": "#4CAF50"}
    for i, col in enumerate(cols):
        if col in df.columns:
            ax = axes[i]
            sns.boxplot(data=df, x="PHYSICIAN", y=col, ax=ax, palette=palette,
                        order=["Dr. A", "Dr. B", "Dr. C"])
            ax.set_title(col.replace("_", " "), fontsize=11)
            ax.set_xlabel("")
            ax.set_ylabel("Minutes")
    plt.suptitle("Step Durations by Physician", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "boxplots_by_physician_steps.png")
    plt.close()
    print("Saved: boxplots_by_physician_steps.png")

    # Also for totals
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, col, title in zip(axes,
        ["CASE_TIME", "SKIN_SKIN", "PT_IN_OUT"],
        ["Case Time", "Skin-to-Skin", "Patient In–Out"]):
        sns.boxplot(data=df, x="PHYSICIAN", y=col, ax=ax, palette=palette,
                    order=["Dr. A", "Dr. B", "Dr. C"])
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("")
        ax.set_ylabel("Minutes")
    plt.suptitle("Total Durations by Physician", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "boxplots_by_physician_totals.png")
    plt.close()
    print("Saved: boxplots_by_physician_totals.png")


def plot_cv_comparison(df):
    """Bar chart of coefficient of variation by step — which step drives variability?"""
    cols = [c for c in STEP_COLS if c in df.columns]
    cvs = df[cols].std() / df[cols].mean()
    cvs = cvs.sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    cvs.plot(kind="bar", ax=ax, color="coral", edgecolor="black")
    ax.set_title("Coefficient of Variation by Procedure Step", fontsize=13)
    ax.set_ylabel("CV (std / mean)")
    ax.set_xlabel("")
    ax.axhline(y=cvs.mean(), color="grey", ls="--", label=f"Mean CV = {cvs.mean():.2f}")
    ax.legend()
    for i, v in enumerate(cvs):
        ax.text(i, v + 0.01, f"{v:.2f}", ha="center", fontsize=9)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "cv_by_step.png")
    plt.close()
    print("Saved: cv_by_step.png")

    cvs.to_csv(RESULTS_DIR / "cv_by_step.csv", header=["CV"])
    return cvs


def plot_correlation_heatmap(df):
    """Correlation heatmap of all numeric duration columns."""
    cols = [c for c in DURATION_COLS + ["NUM_ABL"] if c in df.columns]
    corr = df[cols].corr()
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                ax=ax, square=True, linewidths=0.5)
    ax.set_title("Correlation Matrix — Procedure Durations", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "correlation_heatmap.png")
    plt.close()
    print("Saved: correlation_heatmap.png")


def plot_stacked_duration_breakdown(df):
    """Stacked bar showing mean step durations by physician — where does time go?"""
    cols = ["PT_PREP", "ACCESS", "TSP", "PRE_MAP", "ABL_DURATION", "POST_CARE"]
    means = df.groupby("PHYSICIAN")[cols].mean()
    means = means.loc[["Dr. A", "Dr. B", "Dr. C"]]

    fig, ax = plt.subplots(figsize=(8, 6))
    means.plot(kind="bar", stacked=True, ax=ax, edgecolor="black",
               colormap="Set2")
    ax.set_title("Mean Time Breakdown by Physician", fontsize=13)
    ax.set_ylabel("Minutes")
    ax.set_xlabel("")
    ax.legend(title="Step", bbox_to_anchor=(1.02, 1), loc="upper left",
              labels=[c.replace("_", " ") for c in cols])
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "stacked_duration_by_physician.png")
    plt.close()
    print("Saved: stacked_duration_by_physician.png")


def plot_extra_targets_impact(df):
    """Compare standard PVI vs cases with extra ablation targets."""
    df_plot = df.copy()
    df_plot["Case Type"] = np.where(df_plot["STANDARD_PVI"], "Standard PVI", "Extra Targets / Troubleshoot")

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, col, title in zip(axes,
        ["CASE_TIME", "ABL_DURATION", "PT_IN_OUT"],
        ["Case Time", "Ablation Duration", "Patient In-Out"]):
        sns.boxplot(data=df_plot, x="Case Type", y=col, ax=ax, palette="Set1")
        ax.set_title(title, fontsize=11)
        ax.set_ylabel("Minutes")
        ax.set_xlabel("")
    plt.suptitle("Impact of Extra Ablation Targets on Duration", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "extra_targets_impact.png")
    plt.close()
    print("Saved: extra_targets_impact.png")

    summary = df_plot.groupby("Case Type")[["CASE_TIME", "ABL_DURATION", "PT_IN_OUT"]].agg(["mean", "median", "std", "count"])
    summary.to_csv(RESULTS_DIR / "extra_targets_comparison.csv", float_format="%.1f")
    print("\n=== Extra Targets Impact ===")
    print(summary.round(1).to_string())


def physician_case_mix_crosstab(df):
    """Cross-tab of physician x case complexity — does case mix explain the gap?"""
    # Physician x extra targets
    xtab = pd.crosstab(df["PHYSICIAN"], df["EXTRA_TARGETS"], margins=True)
    xtab.columns = ["Standard PVI", "Extra Targets", "Total"]
    xtab["% Extra"] = (xtab["Extra Targets"] / xtab["Total"] * 100).round(1)
    xtab.to_csv(RESULTS_DIR / "physician_case_mix.csv")
    print("\n=== Physician x Case Complexity ===")
    print(xtab.to_string())

    # Standard PVI only comparison
    std = df[df["STANDARD_PVI"]].copy()
    std_comparison = std.groupby("PHYSICIAN")["CASE_TIME"].agg(["mean", "median", "std", "count"])
    std_comparison.to_csv(RESULTS_DIR / "physician_standard_pvi_only.csv", float_format="%.1f")
    print("\n=== Standard PVI Only — Physician Comparison ===")
    print(std_comparison.round(1).to_string())

    # Detailed note breakdown
    noted = df[df["NOTE"] != ""].copy()
    note_breakdown = noted.groupby("PHYSICIAN")["NOTE"].value_counts()
    note_breakdown.to_csv(RESULTS_DIR / "physician_note_breakdown.csv")
    print("\n=== Detailed Note Breakdown by Physician ===")
    print(note_breakdown.to_string())

    # Visualization
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left: grouped bar of case mix
    mix = pd.DataFrame({
        "Standard PVI": xtab.loc[xtab.index != "All", "Standard PVI"],
        "Extra Targets": xtab.loc[xtab.index != "All", "Extra Targets"],
    })
    mix.plot(kind="bar", ax=axes[0], color=["steelblue", "coral"], edgecolor="black")
    axes[0].set_title("Case Mix by Physician", fontsize=11)
    axes[0].set_ylabel("Number of Cases")
    axes[0].set_xlabel("")
    for container in axes[0].containers:
        axes[0].bar_label(container, fontsize=9)
    axes[0].legend()
    plt.sca(axes[0])
    plt.xticks(rotation=0)

    # Right: standard PVI only case time comparison
    palette = {"Dr. A": "#2196F3", "Dr. B": "#FF9800", "Dr. C": "#4CAF50"}
    sns.boxplot(data=std, x="PHYSICIAN", y="CASE_TIME", ax=axes[1],
                hue="PHYSICIAN", palette=palette, order=["Dr. A", "Dr. B", "Dr. C"],
                legend=False)
    axes[1].set_title("Case Time — Standard PVI Only\n(Extra Targets Removed)", fontsize=11)
    axes[1].set_ylabel("Minutes")
    axes[1].set_xlabel("")
    for phys in ["Dr. A", "Dr. B", "Dr. C"]:
        m = std[std["PHYSICIAN"] == phys]["CASE_TIME"].mean()
        axes[1].text(["Dr. A", "Dr. B", "Dr. C"].index(phys), m + 1.5,
                     f"Mean={m:.0f}", ha="center", fontsize=9, fontweight="bold")

    plt.suptitle("Does Case Mix Explain the Physician Gap?", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "physician_case_mix.png")
    plt.close()
    print("Saved: physician_case_mix.png")


def lab_utilization_analysis(df):
    """Calculate lab utilization by day volume — context for why efficiency matters."""
    day_stats = df.groupby("DATE").agg(
        n_cases=("CASE_NUM", "count"),
        total_pt_time=("PT_IN_OUT", "sum"),
        mean_case_time=("CASE_TIME", "mean"),
        physician=("PHYSICIAN", "first"),
    ).reset_index()

    lab_day_minutes = 540  # 9-hour day assumption
    day_stats["idle_time"] = lab_day_minutes - day_stats["total_pt_time"]
    day_stats["utilization_pct"] = (day_stats["total_pt_time"] / lab_day_minutes * 100).round(1)

    # Summarize by day volume
    util_summary = day_stats.groupby("n_cases").agg(
        num_days=("DATE", "count"),
        avg_total_pt_time=("total_pt_time", "mean"),
        avg_idle_time=("idle_time", "mean"),
        avg_utilization=("utilization_pct", "mean"),
        avg_case_time=("mean_case_time", "mean"),
    ).round(1)
    util_summary.index.name = "cases_per_day"
    util_summary.to_csv(RESULTS_DIR / "lab_utilization.csv")
    print("\n=== Lab Utilization by Day Volume (assuming 9-hr/540-min day) ===")
    print(util_summary.to_string())

    # Visualization
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Left: utilization %
    axes[0].bar(util_summary.index, util_summary["avg_utilization"],
                color="steelblue", edgecolor="black")
    axes[0].set_xlabel("Cases Per Day")
    axes[0].set_ylabel("Lab Utilization (%)")
    axes[0].set_title("Average Lab Utilization by Daily Caseload", fontsize=11)
    axes[0].axhline(y=80, color="red", ls="--", alpha=0.5, label="80% target")
    axes[0].legend()
    for i, row in util_summary.iterrows():
        axes[0].text(i, row["avg_utilization"] + 1.5, f"{row['avg_utilization']:.0f}%",
                     ha="center", fontsize=9)

    # Right: idle time
    axes[1].bar(util_summary.index, util_summary["avg_idle_time"],
                color="coral", edgecolor="black")
    axes[1].set_xlabel("Cases Per Day")
    axes[1].set_ylabel("Idle Time (min)")
    axes[1].set_title("Average Idle Lab Time by Daily Caseload", fontsize=11)
    for i, row in util_summary.iterrows():
        axes[1].text(i, row["avg_idle_time"] + 5, f"{row['avg_idle_time']:.0f} min",
                     ha="center", fontsize=9)

    plt.suptitle("EP Lab Utilization Context (9-hour day = 540 min)", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "lab_utilization.png")
    plt.close()
    print("Saved: lab_utilization.png")


def plot_complexity_vs_performance(df):
    """Scatter: % extra-target cases (complexity) vs mean case time per physician.
    Shows that the fastest physician also handles the most complex cases.
    """
    palette = {"Dr. A": "#2196F3", "Dr. B": "#FF9800", "Dr. C": "#4CAF50"}

    stats = df.groupby("PHYSICIAN").agg(
        mean_case_time=("CASE_TIME", "mean"),
        pct_extra=("EXTRA_TARGETS", "mean"),
        n=("CASE_TIME", "count"),
    ).reset_index()
    stats["pct_extra"] *= 100

    fig, ax = plt.subplots(figsize=(7, 5))

    for _, row in stats.iterrows():
        color = palette.get(row["PHYSICIAN"], "grey")
        ax.scatter(row["pct_extra"], row["mean_case_time"],
                   s=200, color=color, zorder=3, edgecolors="black", linewidths=0.8)
        ax.annotate(
            f"{row['PHYSICIAN']}\n(n={row['n']:.0f})",
            xy=(row["pct_extra"], row["mean_case_time"]),
            xytext=(6, 4), textcoords="offset points",
            fontsize=10, fontweight="bold", color=color,
        )

    ax.set_xlabel("Complex Cases — % With Extra Ablation Targets", fontsize=11)
    ax.set_ylabel("Mean Case Time (min)", fontsize=11)
    ax.set_title(
        "Higher Case Complexity Does NOT Explain Longer Case Times\n"
        "The fastest physician handles the most complex cases",
        fontsize=11,
    )

    # Add a light annotation arrow to reinforce the point
    ax.annotate(
        "Dr. A: most complex cases,\nshortest case time",
        xy=(stats.loc[stats["PHYSICIAN"] == "Dr. A", "pct_extra"].values[0],
            stats.loc[stats["PHYSICIAN"] == "Dr. A", "mean_case_time"].values[0]),
        xytext=(14, 36),
        arrowprops=dict(arrowstyle="->", color="grey"),
        fontsize=9, color="grey",
    )

    ax.set_xlim(-2, 30)
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "complexity_vs_case_time.png")
    plt.close()
    print("Saved: complexity_vs_case_time.png")


def run_eda():
    df = load_and_clean()
    clean = get_clean_subset(df)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PHASE 2: EXPLORATORY DATA ANALYSIS")
    print("=" * 60)

    summary_statistics(clean)
    plot_distributions(clean)
    plot_total_distributions(clean)
    plot_boxplots_by_physician(clean)
    plot_cv_comparison(clean)
    plot_correlation_heatmap(clean)
    plot_stacked_duration_breakdown(clean)
    plot_extra_targets_impact(clean)
    physician_case_mix_crosstab(clean)
    lab_utilization_analysis(clean)
    plot_complexity_vs_performance(clean)

    print("\n" + "=" * 60)
    print("EDA COMPLETE — all figures and CSVs saved to results/")
    print("=" * 60)


if __name__ == "__main__":
    run_eda()
