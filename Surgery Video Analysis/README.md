# Surgery Video Analyzer

**MVP tool for detecting patients and surgeons from overhead OR footage and extracting timestamped events.**

Built for optimizing surgery times by measuring:
- Cycle time (patient-in → patient-out)
- Prep time (patient-in → procedure start)
- Procedure duration
- Turnover time (patient-out → next patient-in)

---

## Quick Start

```bash
# 1. Setup environment (one-time)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Run demo with synthetic video
python main.py demo

# 3. Analyze your own video
python main.py analyze path/to/your/video.mp4
```

---

## Full Setup Guide

### Prerequisites
- Python 3.9+ (3.10 or 3.11 recommended)
- ~2GB disk space for models
- 8GB+ RAM recommended

### Step 1: Create Virtual Environment

**macOS / Linux:**
```bash
cd surgery_analyzer
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
cd surgery_analyzer
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
cd surgery_analyzer
python -m venv venv
venv\Scripts\activate.bat
```

### Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- `opencv-python` - Video processing
- `ultralytics` - YOLOv8 object detection
- `mediapipe` - Pose estimation
- `numpy` - Array operations

**First run will download YOLOv8 model (~6MB).**

### Step 3: Verify Installation

```bash
python -c "from src.analyzer import SurgeryAnalyzer; print('✓ Setup complete!')"
```

---

## Usage

### Generate Synthetic Test Video
```bash
# Quick 5-minute test video
python main.py generate

# Full 40-minute realistic video
python main.py generate --full
```

### Analyze a Video
```bash
# Basic usage
python main.py analyze data/synthetic_surgery_quick.mp4

# With options
python main.py analyze video.mp4 \
    --output results.csv \
    --sample-rate 10 \
    --confidence 0.6
```

**Options:**
| Flag | Default | Description |
|------|---------|-------------|
| `--output`, `-o` | auto | Output CSV path |
| `--sample-rate` | 5 | Process every Nth frame (higher = faster) |
| `--confidence` | 0.5 | Detection confidence threshold |
| `--debounce` | 5.0 | Min seconds between state changes |
| `--max-frames` | None | Stop after N frames (for testing) |

### Run Full Demo
```bash
python main.py demo
```
This generates a synthetic video, analyzes it, and compares results to ground truth.

---

## Output Format

### Events CSV
```csv
event_type,frame_number,timestamp_seconds,timestamp_formatted,details
patient_in,150,5.000,00:00:05.000,"{""num_surgeons"": 3}"
procedure_start,450,15.000,00:00:15.000,"{""num_surgeons"": 3}"
procedure_end,3600,120.000,00:02:00.000,"{}"
patient_out,3900,130.000,00:02:10.000,"{}"
```

### Events JSON
```json
[
  {
    "event_type": "patient_in",
    "frame_number": 150,
    "timestamp_seconds": 5.0,
    "timestamp_formatted": "00:00:05.000",
    "details": {"num_surgeons": 3}
  }
]
```

---

## How It Works

### Detection Pipeline
```
Video Frame
    │
    ▼
┌─────────────────────────┐
│ YOLOv8 Person Detection │  ← Finds all people in frame
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ MediaPipe Pose + BBox   │  ← Determines orientation
│ Aspect Ratio Analysis   │    (horizontal vs vertical)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Role Classification     │  ← Patient: horizontal + on table
│                         │    Surgeon: vertical
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ State Machine           │  ← Tracks transitions:
│                         │    - Patient enters/exits
│                         │    - Procedure starts/ends
└───────────┬─────────────┘
            │
            ▼
    Timestamped Events
```

### State Machine
```
         ┌──────────────────────────────────────────┐
         │                                          │
         ▼                                          │
    ┌─────────┐    patient     ┌──────────────┐     │
    │  IDLE   │ ──detected───▶ │ PATIENT_IN   │     │
    └─────────┘                └──────┬───────┘     │
         ▲                            │             │
         │                   surgeons cluster       │
         │                            │             │
         │                            ▼             │
         │                    ┌──────────────┐      │
         │                    │ PROCEDURE    │      │
         │                    │ ACTIVE       │      │
         │                    └──────┬───────┘      │
         │                           │              │
         │                  surgeons disperse       │
         │                           │              │
         │                           ▼              │
         │                    ┌──────────────┐      │
         │                    │ PROCEDURE    │      │
         │                    │ END          │      │
         │                    └──────┬───────┘      │
         │                           │              │
         │                   patient exits          │
         │                           │              │
         └───────────────────────────┘              │
                                                    │
              Turnover period (no patient) ─────────┘
```

---

## Configuration

### For Real OR Footage

You may need to adjust these parameters in `SurgeryAnalyzer`:

```python
analyzer = SurgeryAnalyzer(
    # Detection sensitivity
    confidence_threshold=0.5,  # Lower = more detections, more false positives
    
    # Define table region (normalized 0-1)
    # Adjust based on your camera angle
    table_region=(0.2, 0.2, 0.8, 0.8),  # (x1, y1, x2, y2)
    
    # How close surgeons must be to patient to count as "clustered"
    cluster_distance=150,  # pixels
    
    # Minimum surgeons around patient to trigger "procedure start"
    min_surgeons_for_procedure=2,
    
    # Prevent rapid state flickering
    debounce_seconds=5.0,
)
```

### Tuning for Your Setup

1. **If patient not detected:** Lower `confidence_threshold` or adjust `table_region`
2. **If too many false detections:** Raise `confidence_threshold`
3. **If procedure start/end flickering:** Increase `debounce_seconds`
4. **If surgeons not clustering:** Increase `cluster_distance`

---

## Project Structure

```
surgery_analyzer/
├── main.py                 # CLI entry point
├── requirements.txt        # Dependencies
├── README.md              # This file
├── src/
│   ├── __init__.py
│   ├── analyzer.py        # Main SurgeryAnalyzer class
│   └── synthetic_video.py # Test video generator
└── data/                  # Generated videos and results
    ├── synthetic_surgery_quick.mp4
    ├── synthetic_surgery_quick.ground_truth.json
    └── demo_results.csv
```

---

## Performance Notes

| Video Length | Sample Rate | Processing Time (approx) |
|--------------|-------------|--------------------------|
| 5 min        | 5           | ~30 sec                  |
| 40 min       | 5           | ~4 min                   |
| 40 min       | 10          | ~2 min                   |

- Higher `sample_rate` = faster but less precise timestamps
- For 30 FPS video, `sample_rate=5` gives ~6 checks/second
- GPU acceleration (if available) significantly speeds up YOLO

---

## Next Steps (Beyond MVP)

### Phase 2: Enhanced Detection
- [ ] Train custom YOLO model on OR footage
- [ ] Add equipment detection (instruments, carts)
- [ ] Track individual surgeon IDs across video

### Phase 3: Workflow Analysis
- [ ] Staff movement heatmaps
- [ ] Parallel vs sequential work detection
- [ ] Congestion zone identification

### Phase 4: Integration
- [ ] Real-time streaming (RTSP)
- [ ] Dashboard visualization
- [ ] EHR integration for ground truth

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'cv2'"**
```bash
pip install opencv-python
```

**"ModuleNotFoundError: No module named 'ultralytics'"**
```bash
pip install ultralytics
```

**YOLO model download fails**
```bash
# Manual download
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
# Place in project root
```

**Low detection accuracy**
- Check camera angle matches expected overhead view
- Adjust `table_region` to match your OR layout
- Try different `confidence_threshold` values

---

## License

MIT License - Use freely for your optimization project.
