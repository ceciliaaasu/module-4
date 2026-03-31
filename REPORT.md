# MSE 433 Module 4 — EP Lab Efficiency Analysis Report

**Course:** MSE 433
**Data:** 150 consecutive AFib ablation cases, 3 physicians, 9 months
**Usable cases after cleaning:** 145 total / 123 standard PVI

---

## 1. Problem Statement

The hospital's Electrophysiology (EP) Lab performs AFib ablation procedures — a repeatable, protocol-driven surgery where the same steps occur for every patient. Despite this, total case time varies widely. The hospital faces high patient demand and long wait times. Understanding the source of variability is the first step toward improving throughput without compromising care quality.

**Key constraint:** Analysis must remain non-punitive toward clinicians. All findings are framed at the process and step level, not as individual performance judgments.

---

## 2. Procedure Overview

Each case follows six sequential phases:

| Step | Description | Avg Duration |
|------|-------------|--------------|
| PT PREP | Positioning, anesthesia, draping | ~19 min |
| ACCESS | Femoral vein puncture, sheath insertion | ~5 min |
| TSP | Transseptal puncture — cross into left atrium | ~5 min |
| PRE-MAP | 3D electrical mapping of heart | ~2 min |
| ABL DURATION | Ablation pulses across target sites | ~24 min |
| POST CARE | Catheter removal, hemostasis, recovery | ~15 min |

**Average total patient in-out time: 79.3 minutes**
22 cases (15%) also included extra ablation targets (CTI, BOX, PST BOX, SVC, AAFL), which add complexity.

---

## 3. Physician Performance Comparison

### 3.1 Raw Averages

| Metric | Dr. A | Dr. B | Dr. C | Overall |
|--------|-------|-------|-------|---------|
| Case Time (min) | 33.6 | 49.4 | 39.7 | 40.7 |
| Patient In-Out (min) | 69.5 | 91.9 | 74.7 | 79.3 |
| TSP (min) | 4.2 | 7.2 | 3.5 | 5.4 |
| ABL Duration (min) | 21.0 | 27.8 | 22.9 | 24.0 |

Dr. B averages **47% more case time** than Dr. A. The gap is concentrated in TSP and ABL DURATION — not in prep or post-care.

### 3.2 Case Mix — Does Complexity Explain the Gap?

| Physician | Standard PVI | Extra Targets | % Extra |
|-----------|-------------|---------------|---------|
| Dr. A | 56 | 14 | 20.0% |
| Dr. B | 53 | 7 | 11.7% |
| Dr. C | 15 | 0 | 0.0% |

**Dr. A handles more complex cases**, yet is still significantly faster. When restricted to standard PVI cases only:

| Physician | Mean Case Time (Standard PVI Only) |
|-----------|------------------------------------|
| Dr. A | 32.0 min |
| Dr. B | 45.5 min |
| Dr. C | 36.6 min |

The gap is **13.5 minutes on identical-complexity cases**. Case mix does not explain the physician difference.

### 3.3 Statistical Confirmation

- ANOVA and Kruskal-Wallis: every step shows statistically significant physician differences (all p < 0.05)
- Tukey HSD: Dr. A vs Dr. B confirmed significant (p < 0.001)
- **Cohen's d = 1.0** for Dr. A vs Dr. B — classified as a large effect
- Dr. C: insufficient sample size (n = 15) for reliable conclusions

The physician gap is real, large, and not attributable to case assignment.

---

## 4. Variance Decomposition — Where Does the Spread Come From?

| Step | % of Total Case Time Variance |
|------|-------------------------------|
| ABL DURATION | **23.9%** |
| TSP | 10.9% |
| PRE-MAP | 10.3% |
| ACCESS | 3.0% |

ABL DURATION is the single largest driver of case-to-case variability. TSP is second — and notable because it has both high relative variability (CV = 0.89) and meaningful absolute impact on case duration.

PRE-MAP has the highest coefficient of variation overall (CV = 1.96) but contributes modestly to total variance due to its short baseline duration.

---

## 5. Outlier Cases

11 cases qualify as statistical outliers (case time > 68 min). **All 11 belong to Dr. B.**

| Case | Duration | Primary Cause |
|------|----------|---------------|
| 57 | 159 min | Extra targets (AAFL + PST BOX) + 95-min ablation |
| 4 | 91 min | 37-min TSP (baseline: ~4 min) |
| 83 | 75 min | 48-min PRE-MAP (baseline: ~1-2 min) |
| Others | 68–75 min | Long TSP or extra ablation targets |

These cases reveal that step-level failures — particularly TSP stalls — can cascade into dramatic total time overruns.

---

## 6. Schedule and Timing Effects

### 6.1 First-Case-of-Day Overhead

| Position | Mean Case Time | n |
|----------|---------------|---|
| First case | 47.3 min | 33 |
| Later cases | 38.8 min | 112 |

**Gap: 8.5 minutes** (Welch t-test p = 0.024; Mann-Whitney p = 0.002)

The first case of the day is consistently and significantly slower. This reflects room setup, equipment calibration, and team warm-up overhead — not patient complexity.

### 6.2 Learning Curves

No statistically significant learning curve was detected for Dr. A (slope = -0.03 min/case, p = 0.53) or Dr. B (slope = -0.05, p = 0.79). These are experienced physicians already at a stable performance plateau. Additional experience will not close the physician gap.

---

## 7. Lab Utilization

| Cases/Day | Avg Utilization | Avg Idle Time |
|-----------|----------------|---------------|
| 1 | 20% | 432 min |
| 2 | 39% | 330 min |
| 4 | 69% | 169 min |
| 5 | 74% | 142 min |
| 6 | 79% | 112 min |
| 7 | 78% | 121 min |

Assumes a 9-hour (540-minute) operating day. On 1-2 case days, the lab sits idle for more than half the day. Utilization approaches 80% on 6-case days.

**Caveat:** Dr. B operates on lower-volume days more frequently (4.6 cases/day vs Dr. A's 5.7). The utilization data cannot isolate whether lower volume causes slower cases, or whether Dr. B's schedule drives both effects. This remains a hypothesis requiring further investigation.

---

## 8. Regression Model Results

**OLS model R² = 0.53** — explains 53% of case time variance.

| Factor | Effect on Case Time | p-value | Significant? |
|--------|-------------------|---------|-------------|
| Being Dr. B (vs Dr. A) | +6.7 min | 0.010 | Yes |
| Being Dr. C (vs Dr. A) | +5.1 min | 0.214 | No |
| Extra ablation targets | +8.6 min | 0.023 | Yes |
| Each additional ablation site | +2.0 min | <0.001 | Yes |
| Each extra minute of TSP | +1.1 min | <0.001 | Yes |
| Each extra minute of PRE-MAP | +1.1 min | <0.001 | Yes |
| Each additional case in experience | -0.18 min | 0.025 | Yes |
| Later position in day | -1.2 min | 0.073 | Borderline |

Even after controlling for case complexity, extra targets, experience, and schedule position, **being Dr. B adds 6.7 minutes per case** — a confirmed physician-specific process effect.

Random Forest feature importance independently confirms the top three predictors: NUM_ABL (0.248), TSP (0.237), PRE_MAP (0.209).

---

## 9. Summary of Findings

### Positive (What's Working)
| Finding | Detail |
|---------|--------|
| Dr. A is highly efficient | Fastest physician, handles the most complex cases |
| Stable procedural steps | PT PREP, ACCESS, POST CARE show low variability and are consistent |
| High-volume days are efficient | ~79% utilization at 6 cases/day — the system can run well |
| Experienced physicians are plateaued | No learning curve gap to close; performance is stable |
| Quantifiable complexity factors | Ablation site count and extra targets are reliable, measurable predictors |

### Negative (Pain Points)
| Finding | Impact |
|---------|--------|
| Dr. B is 47% slower (raw), 42% slower (adjusted) | +13.5 min per case on standard PVI; Cohen's d = 1.0 |
| TSP is the highest-risk step | CV = 0.89; one case saw 37-min TSP vs 4-min baseline; cascades into total delay |
| ABL DURATION drives 24% of all variance | Largest single source of unpredictability |
| All 11 outlier cases are Dr. B | Extreme cases (75–159 min) consistently trace to one physician |
| First-case-of-day costs 8.5 extra minutes | Setup overhead every day; statistically confirmed |
| Low-volume days waste 60–80% of lab time | 1-case days idle for 432 minutes out of 540 |
| 47% of variance is unexplained | Timestamp data ceiling — what happens inside slow steps is invisible |

---

## 10. What the Data Cannot Tell Us

The 47% unexplained variance is the model's ceiling, not its failure. Timestamp data records *when* steps start and end — not *why* they take the time they do. Factors invisible to the current dataset:

- Why TSP occasionally takes 37 minutes instead of 4
- Whether communication delays between team members create hidden wait time
- Whether equipment issues (catheter repositioning, mapping system crashes) drive ablation overruns
- Whether team composition (specific nurse, tech, or fellow) affects coordination
- What physical movement and workflow patterns distinguish fast vs slow cases

---

## 11. Proposed Next Steps (Task 2 Direction)

To close the 47% variance gap, new data collection methods are needed:

| Method | What It Captures | Key Consideration |
|--------|-----------------|-------------------|
| Structured observer checklist (tablet) | Communication events, equipment delays, team coordination | Low-tech, low-disruption; requires trained observer |
| Ambient audio analysis | Communication patterns, call-and-response rates | Privacy and consent required |
| RFID/badge tracking | Staff movement and proximity patterns | Infrastructure investment |
| Computer vision (overhead camera) | Spatial coordination, catheter handling | Highest privacy burden |
| EHR system log integration | Equipment usage, documentation timing | Least disruptive; may be incomplete |

Any proposed method must address: patient and staff privacy/consent, non-disruption to clinical workflow, clinician trust, pilot design, and measurable success criteria.

---

## 12. Recommendations

1. **Investigate TSP and ABL DURATION process differences** between Dr. A and Dr. B — specifically catheter selection, mapping strategy, and energy delivery protocol. The 6.7-minute adjusted gap is real and process-level, not skill-level.

2. **Address first-case-of-day setup overhead** — earlier room prep, standardized pre-case checklists, or scheduling buffer for the first case can recover ~8.5 minutes daily.

3. **Avoid scheduling single-case days** — at 20% utilization, the economic and throughput case is clear. Consolidate to 4+ case days where patient demand allows.

4. **Use ablation site count as a scheduling variable** — each additional site adds 2.0 minutes; this can inform more accurate block scheduling and OR time allocation.

5. **Deploy a structured observer study** to capture the 47% unexplained variance — focus on TSP and ABL DURATION phases during Dr. B's cases vs Dr. A's cases.

---

*Analysis based on 145 usable cases from 150 consecutive AFib ablation procedures. Statistical methods: ANOVA, Kruskal-Wallis, Tukey HSD, OLS regression, Random Forest. All physician comparisons are process-level; no individual performance judgment is implied.*
