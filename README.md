# 💪 GymGuru — Real-time AI Form Coach

> A browser-based, real-time AI fitness coach that watches your workout through
> a webcam, scores your form, counts reps, grades every rep, tracks your
> progress across sessions, and ships Strava / Apple-Health-ready exports.
> Runs **entirely on CPU** on a standard laptop — no GPU, no paid APIs required.

![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![docker](https://img.shields.io/badge/docker-ready-blue)
![mediapipe](https://img.shields.io/badge/MediaPipe-BlazePose-orange)

---

## 🎯 Project in one paragraph

GymGuru turns any laptop with a webcam into a personal strength coach.
A browser captures live video and streams it to a Streamlit server over
**WebRTC**. The server runs **MediaPipe BlazePose** (33 body landmarks)
per frame, applies an **EMA smoother** to kill jitter, computes joint
angles via `atan2`, and feeds a **hysteretic state machine** that counts
reps while capturing *tempo*, *range of motion*, and **per-rep form
grades** (A–F) at the deepest point of each rep. An **unsupervised
anomaly classifier** flags cheat reps, a **workout program runner**
sequences multi-exercise routines with rest timers, and the whole
session can be exported as CSV / JSON / **PDF** / **TCX**
(Strava, Apple Health, Garmin).

---

## 🧱 Tech stack

| Layer | Technology | Why |
|---|---|---|
| **UI** | [Streamlit](https://streamlit.io/) | Zero-frontend interactive app, reactive widgets, download buttons |
| **Live video** | [streamlit-webrtc](https://github.com/whitphx/streamlit-webrtc) + `av` (PyAV) | Browser webcam → server frames, no plugins, zero device config |
| **Pose tracking** | [MediaPipe Tasks API](https://developers.google.com/mediapipe/solutions/vision/pose_landmarker) (BlazePose, 33 landmarks) | State-of-the-art CPU-only pose estimation |
| **Image ops** | [OpenCV](https://opencv.org/) | Frame drawing, overlays, HUD |
| **Math** | NumPy | Vector math, robust statistics |
| **Charts** | [Altair](https://altair-viz.github.io/) + pandas | Contribution heat-map for training streaks |
| **PDF** | [reportlab](https://www.reportlab.com/) | Branded session reports |
| **Speech** | Web Speech API (browser) | Server-free voice cues via `window.speechSynthesis` |
| **Programs** | YAML (`pyyaml`) | Declarative workout templates |
| **Optional LLM** | OpenAI SDK (`openai`) | End-of-session coaching summary (falls back to a local template when no API key) |
| **Deployment** | Docker + docker-compose | One-command reproducible setup |

Key characteristic: **everything is optional and graceful** — heavy pose
model, LLM summaries, history persistence — all controlled by env vars;
the app works without any of them.

---

## ✨ Feature map

### 🎥 Real-time analysis
- **33-landmark pose tracking** (MediaPipe Tasks `PoseLandmarker`).
- **EMA smoothing** on landmark coordinates — dramatically reduces jitter and spurious rep transitions.
- **Joint-angle rules** (2D or opt-in **3D** depth-aware) for depth, alignment, and back angle checks.
- **Hysteretic rep counter** — thresholds with two-level hysteresis avoid double counting.
- **Tempo tracking** — total rep time, eccentric, and concentric phases measured from angle-minimum timestamp.
- **Rep grading A–F** — form score captured at the *deepest* point of each rep (where mistakes are most visible).

### 🧠 Coaching intelligence
- **Per-exercise rules** for 6 exercises (Squat, Push-up, Lunge, Plank, Bicep Curl, Shoulder Press).
- **Symmetry checks** — flags left/right imbalances (*"Uneven squat — L/R knee differ by 22°"*).
- **View calibration** — detects whether you're facing the camera or in side view; warns when it doesn't match the exercise's recommended view.
- **Cheat-rep gating** (#38) — slider to set minimum form score; reps below threshold are *rejected and not counted*, with a visible `Cheat reps: N` counter.
- **Dropout warning** — red banner when the pose is lost for >2s so the user steps back into frame.
- **Rep-quality classifier** (anomaly detection via robust z-score over rep feature vectors) — human-readable reason per outlier (*"depth unusually low"*).

### 🏋️ Workout structure
- **Sets × reps × rest** configuration with automatic rest timer (big overlay on the video).
- **YAML workout programs** (Push Day, Leg Day, Full Body provided) that sequence multiple exercises and auto-advance.
- **End-of-set debrief card** — avg score + worst rep + top issue during rest periods.
- **Pre-rep countdown** — TTS speaks "3, 2, 1" as rest ends.
- **Plank (timed)** — treated as a time-based exercise; counts seconds the body line stays straight.

### 📊 Progress & analytics
- **Per-athlete profiles** — multiple clients, each with their own history file.
- **Streak tracking** — contiguous calendar-day training streak in the sidebar.
- **Heat-map calendar** — GitHub-style contribution grid of training days (26-week view).
- **Personal-record detection** — flags new bests in reps / avg score / seconds held.
- **Progress notes** — automatic observations over the last N sessions (*"📈 Squat: form score up +12 over last 5 sessions"*).
- **Per-rep table** — every rep with grade, depth, duration, and issues.
- **Bar-path diagnostic** — horizontal std-dev of the wrist / shoulder trail in pixels.

### 🎙️ Coaching cues
- **Voice cues** via the browser Web Speech API — speaks rep number and grade, adds top corrective cue when form drops, announces rests and program completion.
- **Adaptive corrective feedback** — the top 3 live issues shown on the HUD each frame.
- **Visual rep flash** — green border on the video the instant a rep completes.
- **HUD overlay** — exercise, set, reps/target, live form score, last grade, cheat-rep count, view warning.

### 📤 Exports & integrations
- **CSV** — per-rep details (grade, depth, tempo, issues).
- **JSON** — full session with reps and summary.
- **PDF report** — branded one-pager with coach-friendly formatting.
- **TCX** — importable into Strava, Apple Health, and Garmin Connect.
- **Optional LLM summary** — end-of-session coaching paragraph via OpenAI (falls back to template when no API key).

### 🚀 Deployment
- **Docker / docker-compose** ready; both the lite and heavy pose models downloaded at build time.
- **Named volume** for per-athlete persistent history.
- **Env-var configurable**: pose model swap, history directory, OpenAI key.

---

## 🏗️ Architecture

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                                Browser                                     │
│  • captures webcam via getUserMedia                                        │
│  • Web Speech API plays TTS coaching cues                                  │
└────────────────────────────────────────────────────────────────────────────┘
                     ▲ video (WebRTC) ▲                  │ TTS JS
                     │                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       Streamlit + streamlit-webrtc                         │
│                                                                            │
│  PoseProcessor.recv(frame):                                                │
│      frame ─▶ PoseDetector ─▶ LandmarkSmoother ─▶ ExerciseAnalyzer.update()│
│                                                     │                      │
│                                                     ├─▶ RepCounter         │
│                                                     ├─▶ SessionTracker     │
│                                                     ├─▶ WorkoutState       │
│                                                     ├─▶ BarPathTracker     │
│                                                     └─▶ RepQualityClassifier
│                                                                            │
│  UI: sidebar (athlete/program/voice)  │  tabs (reps/quality/insights/hist) │
│       ▼                                     ▼                              │
│  export: CSV / JSON / PDF / TCX       persistent history (JSON per athlete)│
└────────────────────────────────────────────────────────────────────────────┘
```

### Data flow per frame

1. Browser captures webcam → WebRTC → server receives `av.VideoFrame`.
2. `PoseDetector` runs MediaPipe `PoseLandmarker` → 33 normalized landmarks.
3. `LandmarkSmoother` applies per-landmark EMA (α=0.6).
4. `ExerciseAnalyzer.update(landmarks)`:
   - Computes form score + feedback.
   - Tracks the deepest frame of the in-progress rep.
   - Feeds the primary joint angle to the `RepCounter`.
   - On rep completion, emits a `RepRecord` captured at the deepest point.
5. `SessionTracker` logs the rep; `WorkoutState` advances sets / triggers rest.
6. `BarPathTracker` adds a wrist/shoulder point to the trail.
7. HUD is drawn on the frame; frame goes back to the browser.
8. Streamlit autorefresh (~400 ms) updates the side-panel metrics.

---

## 📁 Project structure

```
gymguru/
├── app.py                      # Streamlit entry point
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── programs/                   # YAML workout templates
│   ├── push_day.yaml
│   ├── leg_day.yaml
│   └── full_body.yaml
├── core/
│   ├── pose_detector.py        # MediaPipe Tasks wrapper
│   ├── smoother.py             # EMA landmark smoother
│   ├── angle_calculator.py     # 2D / 3D atan2-based angle math
│   ├── symmetry.py             # L/R asymmetry helper
│   ├── bar_path.py             # Wrist/shoulder trajectory tracker
│   ├── rep_counter.py          # Hysteretic rep state machine + tempo
│   ├── exercise_analyzer.py    # Base + RepRecord grading
│   ├── timed_analyzer.py       # Base class for timed exercises (plank)
│   ├── rep_quality.py          # Unsupervised rep anomaly classifier
│   └── program_runner.py       # YAML program sequencer
├── exercises/
│   ├── squat.py
│   ├── pushup.py
│   ├── lunge.py
│   ├── plank.py
│   ├── bicep_curl.py
│   └── shoulder_press.py
├── utils/
│   ├── drawing.py              # Skeleton + HUD overlays
│   ├── calibration.py          # Side-vs-front view detection
│   ├── voice.py                # Browser TTS injection
│   ├── session_tracker.py      # Per-rep tracking + CSV/JSON export
│   ├── workout.py              # Sets/reps/rest state machine
│   ├── history.py              # Per-athlete persistent history
│   ├── progress.py             # PRs, trends, streak, weak-side
│   ├── heatmap.py              # Altair contribution grid
│   ├── pdf_report.py           # ReportLab session report
│   ├── tcx_export.py           # Strava/Apple Health XML export
│   └── llm_summary.py          # Optional OpenAI coach summary
└── tests/
    ├── test_angle_calculator.py
    └── test_new_modules.py     # programs, rep_quality, progress, TCX
```

---

## 🚀 Install & run

### Option A — Docker (recommended)

```bash
git clone <your-fork>
cd gymguru
docker compose up --build
```

Open <http://localhost:8501>.

> ⚠️ **Webcam requires `localhost` or HTTPS** — browsers block `getUserMedia`
> on plain HTTP for any non-localhost URL. For remote deployments put Caddy
> or nginx + Let's Encrypt in front, or use an HTTPS tunnel (Cloudflared,
> ngrok).

### Option B — Local Python (3.10–3.12)

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Download the pose model once (if not using Docker):
mkdir -p models && curl -L \
  -o models/pose_landmarker_lite.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
streamlit run app.py
```

### Tests

```bash
pytest tests/ -q
```

---

## ⚙️ Configuration (environment variables)

| Variable | Default | Effect |
|---|---|---|
| `GYMGURU_POSE_MODEL` | `models/pose_landmarker_lite.task` | Path to the `.task` model. Point at `pose_landmarker_heavy.task` for higher accuracy (costs CPU). |
| `GYMGURU_HISTORY_DIR` | `~/.gymguru/` | Directory where per-athlete `<name>.json` history files are stored. Docker overrides to `/data`. |
| `OPENAI_API_KEY` | *(unset)* | Enables LLM coaching summaries. Without it, a local template is used. |

> 🔐 Copy `.env.example` to `.env` and put your `OPENAI_API_KEY` there.
> `docker compose` reads it automatically. `.env` is gitignored — **do
> not commit secrets**.

---

## 🧑‍🏫 Usage guide

### Starting a session

1. **Athlete** — pick an existing profile or create a new one in the sidebar.
2. **Workout** — choose *Single exercise* (configure sets × reps × rest) or *Program* (auto-sequenced).
3. **Coaching** — toggle voice cues, set the min-quality rep threshold, enable the bar-path trail.
4. Click **START** on the video widget and allow webcam access.

### During the workout

- HUD shows exercise, set `X/Y`, reps `M/N`, live form score, last rep grade.
- Green border flashes on each rep; turns to orange "Last rep: A/B/…" badge.
- Feedback text appears on-frame and under the video.
- Voice calls out each rep and correctives ("go deeper", "hips sagging").
- Once the set target is reached, analysis pauses and the big **REST** overlay counts down. Speech announces "Rest, 60 seconds"; "3, 2, 1" is spoken at the end.
- During rest, an info card shows the set recap: avg score + worst rep & its issue.
- If the pose is lost for >2s, a red *"Pose lost — step back into frame"* banner appears.

### After the workout

- Click **End session & save** — appended to the athlete's history file.
- **Coach summary** is displayed (LLM if configured, otherwise template).
- Download: **CSV** (per-rep), **JSON**, **PDF report**, **TCX** (Strava/Apple Health).
- Switch to the **History** tab to see the contribution heat-map and session table.
- **Insights** tab shows trends, weak-side analysis, and new PRs.

---

## 🧪 How it works — algorithms

### Joint angles

`calculate_angle(p1, p2, p3, use_3d=False)` uses `atan2(|cross|, dot)` on the
vectors `p2→p1` and `p2→p3`, giving a stable 0–180° angle. With `use_3d=True`
the cross product is the 3D vector norm — useful for catching knee valgus
from an angled view.

### Rep counter (hysteresis)

Two thresholds (`down_threshold` and `up_threshold`) prevent noisy
transitions. Example for squats:

```
state = UP
  if angle ≤ 100°:   state = DOWN,   record t_descent_start
  if angle ≥ 160°:   state = UP,     count += 1
                                      emit RepEvent{
                                        duration = now - t_start,
                                        eccentric = t_min - t_start,
                                        concentric = now - t_min,
                                        min_angle = min observed
                                      }
```

### Per-rep grade

Form is scored **every frame**; the score at the **deepest point** of each
rep (minimum primary angle) is kept as the rep's final grade:

| Score | Grade |
|---|---|
| ≥ 90 | A |
| ≥ 80 | B |
| ≥ 65 | C |
| ≥ 50 | D |
| < 50 | F |

### Cheat-rep gating

If the deepest-point score is below the configurable threshold, the rep is
uncounted (`counter.count -= 1`) and tallied as a rejected rep, so the
athlete can't inflate volume with partial reps.

### Rep quality classifier (unsupervised)

Each completed rep is a feature vector
`[score, min_angle, duration_sec, eccentric_sec, concentric_sec]`. We fit a
robust statistic on the athlete's own reps:

```
z_i = 0.6745 * (x_i - median) / MAD(x_i)
```

where MAD = median absolute deviation. Reps with `max |z| > 3` are flagged
with a human-readable reason (*"depth unusually low"*). Because thresholds
are per-athlete, this adapts to individual style without any labeled data.

### View calibration

Side vs front view is detected from the ratio of shoulder horizontal spread
to torso vertical height:

```
ratio = |lsh.x - rsh.x| / |shoulder_mid.y - hip_mid.y|
  ratio > 0.45 → front view
  ratio < 0.25 → side view
```

Each exercise declares `view_hint = "side" | "front" | "any"`; a mismatch
shows an orange chip on the HUD.

### Symmetry

`asymmetry(landmarks, "knee")` returns `|left_knee_angle - right_knee_angle|`.
Thresholds of 15–18° are used to flag imbalances in squat/push-up.

---

## 🐳 Docker details

`docker-compose.yml`:

```yaml
services:
  gymguru:
    build: .
    image: gymguru:latest
    container_name: gymguru
    ports: [ "8501:8501" ]
    restart: unless-stopped
    environment:
      - GYMGURU_HISTORY_DIR=/data
      # - GYMGURU_POSE_MODEL=/app/models/pose_landmarker_heavy.task
      # - OPENAI_API_KEY=sk-...
    volumes:
      - gymguru_data:/data
volumes:
  gymguru_data: {}
```

Both the **lite (~5 MB)** and **heavy (~15 MB)** pose models are downloaded
at build time. Switch at runtime by setting `GYMGURU_POSE_MODEL`.

The container does **not** need device access — the browser captures the
webcam, not the server.

---

## 🧭 Roadmap

Already shipped ✅:

- Real-time 6-exercise analysis, per-rep grading, tempo, ROM
- Workout programs, sets/reps/rest, rest overlay, debrief, pre-rep countdown
- Multi-athlete profiles, history, streaks, heat-map, PR detection, progress notes, weak-side analysis
- Cheat-rep gating, dropout warning, view calibration, symmetry checks
- Bar-path tracking, swappable pose model (lite/heavy), 3D-aware angles
- Voice cues (TTS), CSV/JSON/PDF/TCX exports, optional LLM coach summary
- Rep-quality anomaly classifier (unsupervised)
- Docker / docker-compose deployment

Potential next steps:

- Recorded worst-rep video replay clips
- Coach notes per session + goal tracking
- PDF multi-session athlete report (not just single session)
- Exercise auto-detection (no more dropdown)
- Bigger LLM integration (conversational session review)
- TURN server config for remote WebRTC through strict NATs
- HTTPS reverse proxy (Caddy) in compose for public deployments
- Authentication and multi-coach tenancy

---

## 📜 License

MIT. Use it, fork it, ship it. If you build something cool with it, say hi.
