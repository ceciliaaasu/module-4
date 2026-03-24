# MSE 433 Module 4 — EP Lab Efficiency Analysis
## Complete Team Walkthrough

---

## What Is This Project About?

A hospital's Electrophysiology (EP) Lab performs AFib ablation procedures — a minimally invasive heart procedure where a catheter delivers electrical pulses to stop irregular heartbeats. The same procedure is repeated for every patient, but the time it takes varies a lot. The hospital wants to know why, and what can be done about it.

We were given timestamp data for 150 consecutive cases performed by 3 doctors over 9 months and asked to do two things:

1. **Analyze the data** — explain where the time variability comes from
2. **Propose new observation methods** — suggest how to capture factors the current data doesn't measure (like team coordination, equipment issues, communication breakdowns)

---

## Our Approach: Why We Did What We Did

We chose **variance decomposition** as our core strategy. Instead of treating the total case time as one number and asking "why is it different?", we broke the procedure into its individual steps and asked "which specific step is unstable, and what makes it unstable?"

Why this approach?

- The assignment says we must NOT judge clinician performance. Breaking it down by step keeps the focus on the process, not the person.
- It naturally uses multiple MGTE skills (stats, ML, regression, visualization) — which the rubric heavily rewards under "Integration of Skills."
- It gives actionable outputs. "TSP takes 3 extra minutes on average for Dr. B" is something the hospital can investigate. "Dr. B is slow" is not.

---

## The Procedure — What Each Step Is

Before reading the analysis, you need to understand what happens in the EP Lab. The patient goes through these phases, in order:

| Step | What Happens | Typical Time |
|------|-------------|--------------|
| **PT PREP** | Patient enters, gets positioned, anesthesia, intubation, draping | ~19 min |
| **ACCESS** | Needle puncture into femoral vein, insert sheath | ~5 min |
| **TSP** (Transseptal Puncture) | Cross from right side of heart into left atrium — technically difficult | ~5 min |
| **PRE-MAP** | Build a 3D electrical map of the heart before ablation | ~2 min |
| **ABL DURATION** | Deliver ablation pulses, reposition catheter between sites | ~24 min |
| **POST CARE** | Remove catheters, stop bleeding, wake patient up, monitor | ~15 min |

The total patient time in the lab averages about 79 minutes.

Some cases also involve **extra ablation targets** beyond the standard procedure (noted as CTI, BOX, PST BOX, SVC, or AAFL in the data). These naturally take longer and need to be accounted for.

---

## Step-by-Step Analysis Walkthrough

### Step 1: Data Loading and Cleaning
**File:** `src/data_loading.py`

**What we did:**
- Loaded the Excel file (150 cases, 21 columns)
- Standardized all column names for consistency
- Fixed a date typo in Case 77 ("Juy 21" → July 21, 2025)
- Identified 5 cases with completely missing data (Cases 119, 120, 133, 141, 142) — these are excluded from analysis
- Flagged 22 cases that had extra ablation targets beyond standard PVI
- Flagged 1 case with a "TROUBLESHOOT" note
- Calculated each physician's sequential case number (for learning curve analysis)
- Calculated each case's position within its procedural day (1st case, 2nd case, etc.)

**Why this matters:**
You can't analyze data you don't understand. If we mixed in the cases with extra ablation targets without flagging them, it would make some doctors look slower just because they had harder cases. Cleaning first means every comparison we make later is fair.

**After cleaning:** 145 usable cases, 123 standard PVI cases, 3 physicians (Dr. A: 70 cases, Dr. B: 60 cases, Dr. C: 15 cases).

---

### Step 2: Descriptive Statistics — What Does "Normal" Look Like?
**File:** `src/eda.py` → `summary_statistics()`
**Output:** `results/summary_stats_overall.csv`, `results/summary_stats_by_physician.csv`

**What we did:**
Calculated mean, median, standard deviation, and coefficient of variation (CV) for every procedure step, both overall and broken down by physician.

**Key numbers:**

| Metric | Dr. A | Dr. B | Dr. C | Overall |
|--------|-------|-------|-------|---------|
| Case Time (min) | 33.6 | 49.4 | 39.7 | 40.7 |
| Patient In-Out (min) | 69.5 | 91.9 | 74.7 | 79.3 |
| TSP (min) | 4.2 | 7.2 | 3.5 | 5.4 |
| ABL Duration (min) | 21.0 | 27.8 | 22.9 | 24.0 |

**Why this step is here:**
Before asking "why is there variability?", you need to establish what's typical. You can't spot something abnormal if you don't know what normal looks like. These baseline numbers are what every later comparison is measured against.

**What it tells us:**
Dr. B averages 49.4 minutes of case time compared to 33.6 for Dr. A — a 47% difference. That's huge. But we don't know yet if this is real or just noise, or whether it's Dr. B's fault or his case mix. That's what the next steps figure out.

---

### Step 3: Visual Exploration — Where Are the Differences?
**File:** `src/eda.py` → multiple plot functions
**Output figures:**
- `results/figures/step_distributions.png` — Histograms of each step
- `results/figures/boxplots_by_physician_steps.png` — Box plots per step, per doctor
- `results/figures/boxplots_by_physician_totals.png` — Box plots for total times
- `results/figures/stacked_duration_by_physician.png` — Where does each doctor's time go?
- `results/figures/cv_by_step.png` — Which step is most variable?
- `results/figures/correlation_heatmap.png` — How steps relate to each other
- `results/figures/extra_targets_impact.png` — Standard vs extra-target cases

**What we did:**
Created visualizations that answer: which steps are different across doctors, which steps have the most spread, and how does extra case complexity change things.

**Why this follows Step 2:**
Numbers tell you "Dr. B is slower." Charts tell you *where* and *how*. The stacked bar chart is particularly important — it shows that Dr. B's extra time comes mainly from TSP (transseptal puncture) and ABL DURATION (ablation), not from prep or post-care. That's a specific, investigable finding.

**Key visual findings:**
- The stacked bar chart shows Dr. B's time breakdown is ~81 min vs ~63 min for Dr. A — the gap is almost entirely in TSP and ABL DURATION
- PRE-MAP has the highest coefficient of variation (1.96) — but it's a short step, so the absolute impact is small
- TSP has CV of 0.89 — high relative variability AND meaningful absolute impact
- Extra ablation targets add about 16 minutes on average (54 vs 38 min case time)

---

### Step 3b: Case Mix Cross-Tab — Does Case Complexity Explain the Physician Gap?
**File:** `src/eda.py` → `physician_case_mix_crosstab()`
**Output:** `results/physician_case_mix.csv`, `results/physician_standard_pvi_only.csv`, `results/figures/physician_case_mix.png`

**What we did:**
A natural question after seeing the physician gap: "Maybe Dr. B isn't really slower — maybe he just gets the harder cases." We tested this by cross-tabulating physician against case complexity, and then re-comparing case times using only standard PVI cases (all extra-target cases removed).

**Results:**

| Physician | Standard PVI | Extra Targets | % Extra |
|-----------|-------------|---------------|---------|
| Dr. A | 56 | 14 | 20.0% |
| Dr. B | 53 | 7 | 11.7% |
| Dr. C | 15 | 0 | 0.0% |

**Dr. A actually gets MORE complex cases, not Dr. B.** Dr. A handles 20% extra-target cases vs Dr. B's 12%. And when we remove all those cases and compare standard PVI only:

| Physician | Mean Case Time (Standard PVI Only) |
|-----------|------------------------------------|
| Dr. A | 32.0 min |
| Dr. B | 45.5 min |
| Dr. C | 36.6 min |

The gap barely changes. Dr. B is 13.5 min slower even on identical-complexity cases. Case mix does NOT explain the physician gap.

**Why this matters:**
This is a question someone will ask during the presentation. Having the cross-tab ready shuts it down with evidence. It also reinforces our non-punitive framing — we're not blaming Dr. B, we're showing that the difference is real and isn't explained by case assignment, which means it's worth investigating at the process/technique level.

---

### Step 3c: Lab Utilization Context — Why Efficiency Matters
**File:** `src/eda.py` → `lab_utilization_analysis()`
**Output:** `results/lab_utilization.csv`, `results/figures/lab_utilization.png`

**What we did:**
Calculated how much of each lab day is actually used vs sitting idle, broken down by how many cases are scheduled that day. This assumes a 9-hour (540-minute) operating day.

**Results:**

| Cases/Day | Avg Utilization | Avg Idle Time |
|-----------|----------------|---------------|
| 1 | 20% | 432 min |
| 2 | 39% | 330 min |
| 4 | 69% | 169 min |
| 5 | 74% | 142 min |
| 6 | 79% | 112 min |
| 7 | 78% | 121 min |

On a 1-2 case day, the lab sits idle for 5.5-7 hours. On a 6-case day, utilization approaches 80%.

**Important caveat:** Low-volume days also happen to be days when Dr. B operates more frequently (Dr. B averages 4.6 cases/day vs Dr. A's 5.7). So we cannot separate the "low-volume day" effect from the "Dr. B is on those days" effect using this data alone. The utilization numbers are accurate, but the claim that "consolidating cases would make each case faster" remains a hypothesis, not a proven conclusion.

**Why this is included:**
The slides say the hospital faces "high demand" and "long wait times." These utilization numbers provide context for why improving efficiency matters — even small per-case savings compound into meaningful throughput gains when the lab runs 5-6 cases per day. We present this as context, not as a recommendation.

---

### Step 4: Hypothesis Testing — Are These Differences Real?
**File:** `src/statistical_modeling.py` → `physician_comparison_tests()`, `pairwise_effect_sizes()`
**Output:** `results/physician_hypothesis_tests.csv`, `results/tukey_hsd_case_time.csv`, `results/effect_sizes.csv`

**What we did:**
- ANOVA and Kruskal-Wallis tests across all three physicians for every metric
- Tukey HSD post-hoc test — pairwise comparisons (A vs B, A vs C, B vs C)
- Cohen's d effect sizes — how big is the practical difference?

**Why this follows Step 3:**
Seeing a difference in a chart isn't proof. With 60-70 cases per doctor, random variation could create apparent gaps. Statistical tests tell us whether the differences would be extremely unlikely if the doctors were actually performing identically.

**Results:**
- **Every single step** shows statistically significant differences across physicians (all p < 0.05)
- Dr. A vs Dr. B: confirmed significant (Tukey HSD rejects, p < 0.001)
- Cohen's d = 1.0 for A vs B — this is classified as a "large" effect in statistics
- Dr. A vs Dr. C: NOT significant (p = 0.37) — Dr. C only has 15 cases, not enough statistical power
- Dr. B vs Dr. C: NOT significant (p = 0.09) — same reason, small sample for Dr. C

**What this means in plain English:**
The gap between Dr. A and Dr. B is definitely real — there's less than a 0.1% chance it happened by random variation alone. The gap is also practically large (Cohen's d = 1.0), not just a statistical technicality. We can't say much about Dr. C because we only have 15 cases.

---

### Step 5: Variability Deep Dive — What Specifically Drives the Spread?
**File:** `src/variability_analysis.py`
**Output figures:**
- `results/figures/learning_curves.png` — Do doctors get faster over time?
- `results/figures/learning_curves_steps.png` — Step-level learning trends
- `results/figures/day_position_effect.png` — First case of day vs later cases
- `results/figures/cases_per_day_effect.png` — Does caseload affect performance?
- `results/figures/case_time_timeline.png` — Calendar time trends
- `results/figures/variance_decomposition.png` — Which step drives total variance?
**Output CSVs:**
- `results/outliers.csv` — All extreme cases and their explanations
- `results/variance_decomposition.csv` — Variance contribution per step
- `results/day_position_stats.csv` — Performance by case position in day

**What we did:**

**5a. Variance Decomposition:**
We asked: of the total variance in case time, how much comes from each step?

| Step | % of Total Variance |
|------|-------------------|
| ABL DURATION | 23.9% |
| TSP | 10.9% |
| PRE-MAP | 10.3% |
| ACCESS | 3.0% |

ABL DURATION is the single biggest driver of case-to-case time differences.

**5b. Outlier Analysis:**
We identified 11 cases that are statistical outliers (case time > 68 min). Every single one is Dr. B. The reasons:
- Case 57: 159 min — extra targets (AAFL + PST BOX), 95-minute ablation
- Case 4: 91 min — 37-minute TSP (typical is 4 min)
- Case 83: 75 min — 48-minute PRE-MAP (typical is 1-2 min)
- Most others: long TSP or extra ablation targets

**5c. First Case of Day Effect:**
The first case of the day averages 47.3 minutes. Cases later in the day average 38.8 minutes. This 8.5-minute gap is statistically significant (p = 0.002). By the 5th or 6th case, times are consistently short. This suggests a setup/warm-up overhead that only affects the first case.

**5d. Learning Curves:**
We tested whether doctors get faster as they perform more cases. The answer: no statistically significant learning curve for Dr. A (slope = -0.03 min/case, p = 0.53) or Dr. B (slope = -0.05, p = 0.79). These are experienced physicians — they were already at their stable performance level. Dr. C shows a slight negative trend but with only 15 cases, it's not significant.

**Why this follows Step 4:**
We confirmed the differences are real. Now we need to separate the signal into parts. A doctor being slow could be because of their technique, their case mix (harder patients), their schedule position (always doing the slow first case), or their experience. This step isolates each factor.

---

### Step 6: Regression Model — Putting It All Together
**File:** `src/statistical_modeling.py` → `regression_analysis()`, `feature_importance_rf()`
**Output:** `results/regression_results.csv`, `results/rf_feature_importance.csv`
**Output figure:** `results/figures/regression_diagnostics.png`, `results/figures/rf_feature_importance.png`

**What we did:**
Built an OLS (Ordinary Least Squares) regression model predicting CASE_TIME from all available factors simultaneously:
- Which physician
- Number of ablation sites
- TSP duration
- PRE-MAP duration
- Whether the case had extra targets
- Physician's cumulative case number (experience)
- Position of the case in the day's schedule

**Why this follows Step 5:**
Steps 2-5 looked at each factor individually. But factors might be correlated — maybe Dr. B gets more extra-target cases, so his slower time isn't entirely about his technique. Regression controls for everything at once and tells us the *independent* effect of each factor.

**Results (R-squared = 0.53 — the model explains 53% of the variance):**

| Factor | Effect on Case Time | p-value | Significant? |
|--------|-------------------|---------|-------------|
| Being Dr. B (vs Dr. A) | +6.7 min | 0.010 | Yes |
| Being Dr. C (vs Dr. A) | +5.1 min | 0.214 | No |
| Extra ablation targets | +8.6 min | 0.023 | Yes |
| Each additional ablation site | +2.0 min | <0.001 | Yes |
| Each extra minute of TSP | +1.1 min | <0.001 | Yes |
| Each extra minute of PRE-MAP | +1.1 min | <0.001 | Yes |
| Each additional case in experience | -0.18 min | 0.025 | Yes |
| Each later position in the day | -1.2 min | 0.073 | Borderline |

**What this means in plain English:**
Even after controlling for case complexity, extra targets, experience, and schedule position, being Dr. B still adds 6.7 minutes to a case. This is a real physician-specific effect.

But more importantly: TSP and PRE-MAP are the high-leverage steps. When TSP takes longer than expected, it cascades through the rest of the case. And the number of ablation sites is the strongest predictor — each additional site adds 2 full minutes.

**The critical finding:** 47% of the variance is unexplained. The timestamp data simply cannot tell us what's happening during the variable steps. This is the evidence-based justification for Task 2 — proposing new data collection methods.

We also ran a Random Forest model for feature importance ranking. The top 3 features: NUM_ABL (0.248), TSP (0.237), PRE_MAP (0.209). This confirms the OLS findings using a completely different method.

---

### Step 7: First-Case Effect Confirmation
**File:** `src/statistical_modeling.py` → `first_case_effect()`
**Output:** `results/first_case_effect.csv`

**What we did:**
Formal statistical test comparing first-case-of-day vs all other cases.

**Results:**
- First case: mean = 47.3 min, n = 33
- Later cases: mean = 38.8 min, n = 112
- Welch t-test: p = 0.024
- Mann-Whitney (one-sided): p = 0.002

Both tests confirm: the first case of the day is significantly slower. This is likely a setup and warm-up effect — room preparation, equipment calibration, team settling in.

---

## Summary of All Findings

### What the data tells us:

1. **Dr. B's cases take significantly longer** (+15.8 min vs Dr. A, even after adjustment: +6.7 min), driven primarily by longer TSP and ABL DURATION times
2. **Case mix does NOT explain the gap** — Dr. A actually gets more complex cases (20% extra targets vs 12%), yet is still faster. On standard PVI only, the gap persists (32.0 vs 45.5 min)
3. **ABL DURATION is the biggest variance driver** (24% of total), followed by TSP (11%) and PRE-MAP (10%)
4. **Extra ablation targets add ~8.6 min** — these need to be accounted for when comparing performance
5. **The first case of the day costs ~8.5 extra minutes** — a setup/warm-up overhead
6. **All 11 outlier cases belong to Dr. B** — most caused by abnormally long TSP or extra targets
7. **No significant learning curve** for the experienced physicians (Dr. A, Dr. B)
8. **Lab utilization ranges from 20% on 1-case days to 79% on 6-case days** — efficiency improvements compound into meaningful throughput gains
9. **47% of variance is unexplained** by the available data — this motivates new data collection

### What the data CANNOT tell us (→ Task 2):

- Why TSP sometimes takes 37 minutes instead of 4
- Whether communication breakdowns cause delays
- Whether equipment logistics create hidden downtime
- Whether team composition (which nurse, which tech) matters
- What physical movements and coordination patterns look like during slow vs fast cases

---

## What Still Needs To Be Done

### Task 2: Propose Unobserved Factor Capture Method
This is the second required deliverable. Using the 47% unexplained variance as justification, we need to propose a method for capturing what the timestamps can't see. Possible directions:

- Ambient audio analysis for communication patterns
- Structured observer checklists via tablet
- RFID/badge tracking for staff movement
- Computer vision for spatial awareness
- EHR system log integration

The proposal must address: privacy/consent, clinician trust, non-disruption to clinical care, pilot design, and how you'd know if the method works.

### Report
Structure: Problem → Data → EDA → Statistical Analysis → Findings → Proposed Method → Recommendations

### Presentation (April 2)
Key visuals to feature: stacked bar chart, learning curves, regression coefficient table, variance decomposition bar chart.

---

## How to Run the Code

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run everything (generates all CSVs and figures)
python3 run_all.py
```

The data file (`MSE433_M4_Data.xlsx`) must be in the parent directory (one level up from this folder).

---

## File Structure

```
Team Deliverable/
├── WALKTHROUGH.md           ← You are here
├── run_all.py               ← Run this to reproduce everything
├── requirements.txt         ← Python dependencies
├── src/
│   ├── data_loading.py      ← Step 1: Load and clean data
│   ├── eda.py               ← Steps 2-3: Descriptive stats and visuals
│   ├── variability_analysis.py  ← Step 5: Variance, outliers, learning curves
│   └── statistical_modeling.py  ← Steps 4, 6, 7: Tests, regression, RF
└── results/
    ├── summary_stats_overall.csv
    ├── summary_stats_by_physician.csv
    ├── cv_by_step.csv
    ├── extra_targets_comparison.csv
    ├── physician_case_mix.csv              ← NEW: case mix cross-tab
    ├── physician_standard_pvi_only.csv     ← NEW: standard PVI comparison
    ├── physician_note_breakdown.csv        ← NEW: detailed note types per doctor
    ├── lab_utilization.csv                 ← NEW: utilization by day volume
    ├── physician_hypothesis_tests.csv
    ├── tukey_hsd_case_time.csv
    ├── effect_sizes.csv
    ├── outliers.csv
    ├── variance_decomposition.csv
    ├── day_position_stats.csv
    ├── regression_results.csv
    ├── rf_feature_importance.csv
    ├── learning_curve_regression.csv
    ├── first_case_effect.csv
    └── figures/
        ├── step_distributions.png
        ├── total_duration_distributions.png
        ├── boxplots_by_physician_steps.png
        ├── boxplots_by_physician_totals.png
        ├── stacked_duration_by_physician.png
        ├── cv_by_step.png
        ├── correlation_heatmap.png
        ├── extra_targets_impact.png
        ├── physician_case_mix.png          ← NEW: case mix vs standard PVI
        ├── lab_utilization.png             ← NEW: utilization and idle time
        ├── learning_curves.png
        ├── learning_curves_steps.png
        ├── day_position_effect.png
        ├── cases_per_day_effect.png
        ├── case_time_timeline.png
        ├── variance_decomposition.png
        ├── regression_diagnostics.png
        └── rf_feature_importance.png
```
