# Module 4: Operating Room Efficiency Analysis

A dual-module research project analyzing surgical procedure efficiency through statistical data analysis and computer vision-based video analysis.

## Overview

This repository contains two complementary approaches to studying operating room (OR) efficiency:

1. **Part 1 Analysis** — Statistical analysis of procedure time data across physicians, procedure steps, and case complexity
2. **Surgery Video Analysis** — A computer vision tool that automatically extracts procedure timing from overhead OR camera footage

---

## Repository Structure

```
module-4/
├── run_all.py                   # Orchestrator: runs all Part 1 analysis phases
├── requirements.txt             # Dependencies for Part 1 Analysis
│
├── Part 1 Analysis/
│   ├── src/
│   │   ├── data_loading.py      # Data import, cleaning, and preprocessing
│   │   ├── eda.py               # Exploratory data analysis and visualizations
│   │   ├── statistical_modeling.py  # Hypothesis tests, regression, ML
│   │   └── variability_analysis.py  # Learning curves and outlier detection
│   └── results/                 # Generated CSV summaries and PNG plots
│
└── Surgery Video Analysis/
    ├── main.py                  # CLI entry point
    ├── requirements.txt         # Dependencies for video analysis
    ├── README.md                # Detailed documentation for this module
    └── src/
        ├── analyzer.py          # Core video processing engine
        └── synthetic_video.py   # Synthetic test video generator
```

---

## Part 1 Analysis

Statistical analysis of surgical procedure time data to identify performance differences, learning effects, and workload complexity across physicians.

### Setup

```bash
pip install -r requirements.txt
```

### Usage

Run all three analysis phases in sequence:

```bash
python run_all.py
```

This executes:
1. **EDA** (`eda.py`) — Distributions, box plots, correlation matrices, physician comparisons, lab utilization
2. **Variability Analysis** (`variability_analysis.py`) — Learning curves, day-position effects, variance decomposition, outlier detection
3. **Statistical Modeling** (`statistical_modeling.py`) — ANOVA, Kruskal-Wallis tests, OLS regression, random forest feature importance

### Output

Results are saved to `Part 1 Analysis/results/`:
- CSV files with statistical summaries and test results
- PNG files with publication-quality figures

### Key Metrics Analyzed

| Metric | Description |
|--------|-------------|
| `CASE_TIME` | Total case duration |
| `SKIN_SKIN` | Skin-to-skin procedure time |
| `PT_IN_OUT` | Full patient in/out time |
| `PT_PREP` | Patient preparation time |
| `ACCESS` | Access procedure time |
| `ABL_DURATION` | Ablation duration |
| `LA_DWELL` | LA dwell time |

---

## Surgery Video Analysis

A computer vision MVP that processes overhead OR camera footage to automatically detect and timestamp key surgical events.

### Setup

```bash
cd "Surgery Video Analysis"
pip install -r requirements.txt
```

### Usage

**Generate synthetic test videos:**
```bash
python main.py generate
python main.py generate --full   # longer video
```

**Analyze a real OR video:**
```bash
python main.py analyze <video_path>
python main.py analyze <video_path> --sample-rate 5 --confidence 0.6
```

**Run a full demo (generate + analyze):**
```bash
python main.py demo
```

### How It Works

1. Background subtraction and contour detection identify moving entities in each frame
2. Role classification distinguishes patients from surgical staff
3. A state machine tracks transitions: `idle → patient_in → procedure_active → patient_out`
4. Timestamped events are exported as CSV and JSON

### Output Events

| Event | Description |
|-------|-------------|
| `patient_in` | Patient enters the OR |
| `procedure_start` | Surgical procedure begins |
| `procedure_end` | Surgical procedure ends |
| `patient_out` | Patient leaves the OR |

Derived metrics include cycle time, prep time, procedure duration, and turnover time.

For full documentation, see [`Surgery Video Analysis/README.md`](Surgery%20Video%20Analysis/README.md).

---

## Dependencies

**Part 1 Analysis:** `pandas`, `numpy`, `scipy`, `statsmodels`, `scikit-learn`, `matplotlib`, `seaborn`, `openpyxl`, `python-pptx`

**Surgery Video Analysis:** `opencv-python`, `ultralytics` (YOLOv8), `mediapipe`, `numpy`, `tqdm`

---

## Requirements

- Python 3.9+
- Input data file: `MSE433_M4_Data.xlsx` (required for Part 1 Analysis)
