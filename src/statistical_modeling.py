"""
Statistical modeling: hypothesis tests, regression, factor analysis for EP Lab durations.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score

from data_loading import (
    load_and_clean, get_clean_subset, get_standard_pvi,
    STEP_COLS, RESULTS_DIR, FIGURES_DIR,
)

plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "font.size": 10})
PALETTE = {"Dr. A": "#2196F3", "Dr. B": "#FF9800", "Dr. C": "#4CAF50"}


# =========================================================
# 1. Hypothesis Testing — Physician Differences
# =========================================================

def physician_comparison_tests(df):
    """ANOVA and Kruskal-Wallis for CASE_TIME across physicians, plus Tukey HSD."""
    results = []

    for col in ["CASE_TIME", "SKIN_SKIN", "PT_IN_OUT", "PT_PREP", "TSP", "PRE_MAP", "ABL_DURATION", "POST_CARE"]:
        groups = [grp[col].dropna().values for _, grp in df.groupby("PHYSICIAN")]

        # Kruskal-Wallis (non-parametric)
        kw_stat, kw_p = stats.kruskal(*groups)

        # One-way ANOVA
        f_stat, anova_p = stats.f_oneway(*groups)

        results.append({
            "Variable": col,
            "ANOVA F": round(f_stat, 2),
            "ANOVA p": round(anova_p, 4),
            "Kruskal H": round(kw_stat, 2),
            "Kruskal p": round(kw_p, 4),
            "Significant (p<0.05)": "Yes" if kw_p < 0.05 else "No",
        })

    results_df = pd.DataFrame(results)
    results_df.to_csv(RESULTS_DIR / "physician_hypothesis_tests.csv", index=False)
    print("\n=== Physician Comparison Tests ===")
    print(results_df.to_string(index=False))

    # Tukey HSD for CASE_TIME
    tukey = pairwise_tukeyhsd(df["CASE_TIME"].values, df["PHYSICIAN"].values, alpha=0.05)
    print("\n=== Tukey HSD — CASE_TIME ===")
    print(tukey)

    tukey_df = pd.DataFrame(data=tukey._results_table.data[1:], columns=tukey._results_table.data[0])
    tukey_df.to_csv(RESULTS_DIR / "tukey_hsd_case_time.csv", index=False)

    return results_df


def pairwise_effect_sizes(df):
    """Cohen's d for each physician pair on CASE_TIME."""
    pairs = [("Dr. A", "Dr. B"), ("Dr. A", "Dr. C"), ("Dr. B", "Dr. C")]
    results = []
    for p1, p2 in pairs:
        g1 = df[df["PHYSICIAN"] == p1]["CASE_TIME"].dropna()
        g2 = df[df["PHYSICIAN"] == p2]["CASE_TIME"].dropna()
        pooled_std = np.sqrt(((len(g1)-1)*g1.var() + (len(g2)-1)*g2.var()) / (len(g1)+len(g2)-2))
        d = (g1.mean() - g2.mean()) / pooled_std
        results.append({"Comparison": f"{p1} vs {p2}", "Cohen's d": round(d, 3),
                        "Mean1": round(g1.mean(), 1), "Mean2": round(g2.mean(), 1),
                        "Diff": round(g1.mean() - g2.mean(), 1)})
    results_df = pd.DataFrame(results)
    results_df.to_csv(RESULTS_DIR / "effect_sizes.csv", index=False)
    print("\n=== Pairwise Effect Sizes (Cohen's d) — CASE_TIME ===")
    print(results_df.to_string(index=False))
    return results_df


# =========================================================
# 2. Regression — What Drives CASE_TIME?
# =========================================================

def regression_analysis(df):
    """OLS regression for CASE_TIME using available predictors."""
    df_reg = df.copy()

    # Encode physician as dummies (Dr. A as baseline)
    df_reg["is_DrB"] = (df_reg["PHYSICIAN"] == "Dr. B").astype(int)
    df_reg["is_DrC"] = (df_reg["PHYSICIAN"] == "Dr. C").astype(int)
    df_reg["has_extra"] = df_reg["EXTRA_TARGETS"].astype(int)

    feature_cols = [
        "is_DrB", "is_DrC", "has_extra",
        "NUM_ABL", "TSP", "PRE_MAP",
        "PHYSICIAN_CASE_SEQ", "DAY_POSITION"
    ]

    df_model = df_reg[feature_cols + ["CASE_TIME"]].dropna()
    X = df_model[feature_cols]
    y = df_model["CASE_TIME"]

    X_const = sm.add_constant(X)
    model = sm.OLS(y, X_const).fit()

    print("\n=== OLS Regression: CASE_TIME ===")
    print(model.summary())

    # Save results
    summary_df = pd.DataFrame({
        "Coefficient": model.params.round(3),
        "Std Error": model.bse.round(3),
        "t-stat": model.tvalues.round(2),
        "p-value": model.pvalues.round(4),
    })
    summary_df.to_csv(RESULTS_DIR / "regression_results.csv")

    # Residual plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].scatter(model.fittedvalues, model.resid, alpha=0.5, s=20)
    axes[0].axhline(0, color="red", ls="--")
    axes[0].set_xlabel("Fitted Values")
    axes[0].set_ylabel("Residuals")
    axes[0].set_title("Residuals vs Fitted")

    stats.probplot(model.resid, dist="norm", plot=axes[1])
    axes[1].set_title("Q-Q Plot of Residuals")

    plt.suptitle(f"OLS Diagnostics (R² = {model.rsquared:.3f}, Adj R² = {model.rsquared_adj:.3f})", fontsize=12)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "regression_diagnostics.png")
    plt.close()
    print("Saved: regression_diagnostics.png")

    return model


def feature_importance_rf(df):
    """Random Forest feature importance for CASE_TIME."""
    df_rf = df.copy()
    df_rf["is_DrB"] = (df_rf["PHYSICIAN"] == "Dr. B").astype(int)
    df_rf["is_DrC"] = (df_rf["PHYSICIAN"] == "Dr. C").astype(int)
    df_rf["has_extra"] = df_rf["EXTRA_TARGETS"].astype(int)

    feature_cols = [
        "is_DrB", "is_DrC", "has_extra",
        "NUM_ABL", "TSP", "PRE_MAP", "ACCESS",
        "PHYSICIAN_CASE_SEQ", "DAY_POSITION"
    ]

    df_model = df_rf[feature_cols + ["CASE_TIME"]].dropna()
    X = df_model[feature_cols]
    y = df_model["CASE_TIME"]

    rf = RandomForestRegressor(n_estimators=200, random_state=42, max_depth=8)
    rf.fit(X, y)

    # Cross-validation R²
    cv_scores = cross_val_score(rf, X, y, cv=5, scoring="r2")

    importances = pd.Series(rf.feature_importances_, index=feature_cols).sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(9, 5))
    importances.plot(kind="bar", ax=ax, color="teal", edgecolor="black")
    ax.set_title(f"Random Forest Feature Importance (CV R² = {cv_scores.mean():.3f} ± {cv_scores.std():.3f})",
                 fontsize=12)
    ax.set_ylabel("Importance")
    for i, v in enumerate(importances):
        ax.text(i, v + 0.005, f"{v:.3f}", ha="center", fontsize=9)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "rf_feature_importance.png")
    plt.close()
    print(f"\nSaved: rf_feature_importance.png")

    importances.to_csv(RESULTS_DIR / "rf_feature_importance.csv", header=["Importance"])
    print(f"\n=== Random Forest Feature Importance (5-fold CV R² = {cv_scores.mean():.3f}) ===")
    print(importances.round(3).to_string())

    return importances


# =========================================================
# 3. Learning Curve Significance
# =========================================================

def learning_curve_regression(df):
    """Test if PHYSICIAN_CASE_SEQ significantly predicts shorter CASE_TIME per physician."""
    print("\n=== Learning Curve Regression (per physician) ===")
    results = []
    for phys in ["Dr. A", "Dr. B", "Dr. C"]:
        sub = df[df["PHYSICIAN"] == phys][["PHYSICIAN_CASE_SEQ", "CASE_TIME"]].dropna()
        if len(sub) < 10:
            continue
        X = sm.add_constant(sub["PHYSICIAN_CASE_SEQ"])
        model = sm.OLS(sub["CASE_TIME"], X).fit()
        coef = model.params["PHYSICIAN_CASE_SEQ"]
        pval = model.pvalues["PHYSICIAN_CASE_SEQ"]
        r2 = model.rsquared
        results.append({
            "Physician": phys,
            "Slope (min/case)": round(coef, 3),
            "p-value": round(pval, 4),
            "R²": round(r2, 3),
            "Significant": "Yes" if pval < 0.05 else "No",
            "n_cases": len(sub),
        })
        print(f"  {phys}: slope={coef:.3f} min/case, p={pval:.4f}, R²={r2:.3f}, n={len(sub)}")

    results_df = pd.DataFrame(results)
    results_df.to_csv(RESULTS_DIR / "learning_curve_regression.csv", index=False)
    return results_df


# =========================================================
# 4. First-Case-of-Day Effect
# =========================================================

def first_case_effect(df):
    """Test whether the first case of the day is significantly slower."""
    df_test = df.copy()
    df_test["IS_FIRST"] = (df_test["DAY_POSITION"] == 1).astype(int)

    first = df_test[df_test["IS_FIRST"] == 1]["CASE_TIME"].dropna()
    later = df_test[df_test["IS_FIRST"] == 0]["CASE_TIME"].dropna()

    t_stat, t_p = stats.ttest_ind(first, later, equal_var=False)
    mw_stat, mw_p = stats.mannwhitneyu(first, later, alternative="greater")

    print(f"\n=== First Case of Day Effect ===")
    print(f"  First case: mean={first.mean():.1f}, median={first.median():.0f}, n={len(first)}")
    print(f"  Later cases: mean={later.mean():.1f}, median={later.median():.0f}, n={len(later)}")
    print(f"  Welch t-test: t={t_stat:.2f}, p={t_p:.4f}")
    print(f"  Mann-Whitney (one-sided): U={mw_stat:.0f}, p={mw_p:.4f}")

    result = {
        "First_mean": round(first.mean(), 1),
        "Later_mean": round(later.mean(), 1),
        "Difference": round(first.mean() - later.mean(), 1),
        "t_stat": round(t_stat, 2),
        "t_pvalue": round(t_p, 4),
        "MW_pvalue": round(mw_p, 4),
    }
    pd.DataFrame([result]).to_csv(RESULTS_DIR / "first_case_effect.csv", index=False)
    return result


def run_statistical_modeling():
    df = load_and_clean()
    clean = get_clean_subset(df)
    std = get_standard_pvi(df)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PHASE 3: STATISTICAL MODELING")
    print("=" * 60)

    physician_comparison_tests(clean)
    pairwise_effect_sizes(clean)
    regression_analysis(clean)
    feature_importance_rf(clean)
    learning_curve_regression(clean)
    first_case_effect(clean)

    print("\n" + "=" * 60)
    print("STATISTICAL MODELING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_statistical_modeling()
