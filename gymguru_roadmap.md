# GymGuru — Roadmap & Claude Code Prompt

> **Project:** Real-time workout form checker using webcam + pose estimation.
> **Stack:** Python, MediaPipe, OpenCV, Streamlit, NumPy.
> **Duration:** 3 weeks (solo student).

---

## 1. Professional Prompt for Claude Code

Copy-paste the block below into Claude Code to bootstrap the entire project.

```
# ROLE
You are a senior Python engineer specialized in computer vision and real-time
applications. You write clean, modular, production-quality code with clear
comments and proper error handling. You follow PEP 8 and prefer small,
testable functions.

# PROJECT
Build "GymGuru" — a real-time AI-powered workout form checker that:
1. Reads webcam video feed live
2. Detects human body landmarks using MediaPipe Pose
3. Analyzes exercise form (squats, push-ups, bicep curls) via joint-angle rules
4. Counts repetitions automatically
5. Provides visual feedback (green/red joint overlays) and textual corrections
6. Displays everything in a Streamlit web app
7. Tracks a session history (reps, form score, common mistakes)

# TECHNICAL CONSTRAINTS
- Language: Python 3.10+
- Core libraries: mediapipe, opencv-python, streamlit, streamlit-webrtc, numpy
- NO heavy deep learning training — MediaPipe handles pose detection out of the box
- NO paid APIs, NO GPU required
- Must run on a standard laptop with a basic webcam
- All logic should be CPU-friendly (target: 15+ FPS)

# PROJECT STRUCTURE
Create the following structure:
gymguru/
├── app.py                      # Streamlit entry point
├── requirements.txt
├── README.md
├── core/
│   ├── __init__.py
│   ├── pose_detector.py        # MediaPipe wrapper
│   ├── angle_calculator.py     # Joint angle math utilities
│   ├── exercise_analyzer.py    # Base class + per-exercise rules
│   └── rep_counter.py          # State machine for counting reps
├── exercises/
│   ├── __init__.py
│   ├── squat.py
│   ├── pushup.py
│   └── bicep_curl.py
├── utils/
│   ├── __init__.py
│   ├── drawing.py              # Overlay rendering (joints, feedback text)
│   └── session_tracker.py      # Per-session stats
└── tests/
    └── test_angle_calculator.py

# IMPLEMENTATION RULES
1. `pose_detector.py`: wrap MediaPipe Pose, return a dict of landmark coords.
2. `angle_calculator.py`: function `calculate_angle(p1, p2, p3)` using atan2.
3. Each exercise module exports a class inheriting from `ExerciseAnalyzer` with:
   - `check_form(landmarks) -> (score: float, feedback: list[str])`
   - `detect_rep(landmarks) -> bool` (uses up/down state machine)
4. `app.py` uses streamlit-webrtc for live webcam streaming.
5. UI: exercise selector (dropdown), live video feed with overlays, rep counter,
   form score (0–100), real-time feedback messages, end-of-session summary.
6. Add docstrings to every public function.
7. Add unit tests for `angle_calculator.py`.

# DELIVERABLES
Deliver all files above in a single pass. End with:
- A `requirements.txt` pinned to known-good versions.
- A `README.md` with install, run, and usage instructions.
- A short "How it works" section explaining the angle-based rules.

# STYLE
- Compact, readable code. No over-engineering.
- Type hints everywhere.
- Handle the case where the webcam is not available gracefully.
- Log key events with Python's `logging` module (not print).

Start by creating the folder structure, then implement files in this order:
angle_calculator → pose_detector → rep_counter → exercise base class →
squat → pushup → bicep_curl → drawing utils → session_tracker → app.py →
tests → requirements.txt → README.md.
```

---

## 2. 3-Week Roadmap

### Week 1 — Foundations & Pose Detection

**Goal:** Get a working webcam feed with live pose overlay.

| Day | Task |
|-----|------|
| 1   | Set up Python venv, install mediapipe, opencv, streamlit. Run MediaPipe demo. |
| 2   | Build `pose_detector.py` — wrap MediaPipe, return landmark dict. |
| 3   | Build `angle_calculator.py` — calculate 2D joint angles. Write unit tests. |
| 4   | Prototype raw OpenCV webcam loop with live skeleton overlay. |
| 5   | Migrate to Streamlit + streamlit-webrtc for browser-based demo. |
| 6–7 | Polish overlay drawing (colored joints, FPS counter). Commit to Git. |

**Milestone:** Open webcam in browser, see live skeleton drawn on your body.

---

### Week 2 — Exercise Logic & Rep Counting

**Goal:** Squat, push-up, and bicep curl analyzers working with form feedback.

| Day  | Task |
|------|------|
| 8    | Design `ExerciseAnalyzer` base class + state machine for reps. |
| 9    | Implement `squat.py` (knee angle, back angle, depth check). |
| 10   | Implement `pushup.py` (elbow angle, body alignment). |
| 11   | Implement `bicep_curl.py` (elbow flexion, shoulder stability). |
| 12   | Tune thresholds using your own webcam recordings. |
| 13   | Add feedback text overlay: "Go deeper", "Keep back straight", etc. |
| 14   | Integrate rep counting with audio cues (optional beep on each rep). |

**Milestone:** Do 10 squats in front of the webcam; app counts them and flags bad form.

---

### Week 3 — UI, Polish & Demo Prep

**Goal:** Professional-looking app + memorable presentation.

| Day  | Task |
|------|------|
| 15   | Build exercise selector dropdown + session start/stop buttons. |
| 16   | Implement `session_tracker.py` — store reps, avg form score, top mistakes. |
| 17   | Add end-of-session summary screen with charts (matplotlib/plotly). |
| 18   | Style the Streamlit app (custom CSS, logo, color theme). |
| 19   | Record demo video + prepare slide deck (problem, approach, results). |
| 20   | Write README, project report, and technical documentation. |
| 21   | **Final dress rehearsal** — present to a friend, collect feedback, fix bugs. |

**Milestone:** Live demo + 2-minute pitch ready.

---

## 3. Bonus Features (If Ahead of Schedule)

- **Progress tracking:** persist sessions to JSON/SQLite, show weekly form improvement graph.
- **Voice feedback:** use `pyttsx3` to speak corrections aloud.
- **Exercise library:** add lunges, planks, shoulder press.
- **Form score leaderboard:** gamify with friends.
- **Export PDF report:** end-of-session summary as a downloadable PDF.

---

## 4. Presentation Checklist (Impress Your Professor)

- [ ] Clear problem statement (70% gym injuries from bad form, trainers cost $60/hr).
- [ ] Live webcam demo — do a squat in front of the class.
- [ ] Show real-time form feedback (green joints good, red joints bad).
- [ ] Show session summary chart.
- [ ] Explain the angle-based rule system in under 90 seconds.
- [ ] Mention limitations honestly (2D only, lighting sensitivity).
- [ ] Propose realistic extensions (mobile app, ML-based form scoring).

---

## 5. Verification Commands

```bash
# Install
pip install -r requirements.txt

# Run tests
pytest tests/

# Launch app
streamlit run app.py
```

---

**Final tip:** Record a backup demo video in case the webcam or network fails during the live presentation. Always have a plan B.
