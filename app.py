"""GymGuru — Streamlit entry point (v4).

Run with:  streamlit run app.py
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import av
import cv2
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_webrtc import WebRtcMode, webrtc_streamer

from core.bar_path import BarPathTracker
from core.pose_detector import PoseDetector
from core.program_runner import ProgramRunner, load_programs
from core.rep_quality import RepQualityClassifier
from core.smoother import LandmarkSmoother
from exercises import EXERCISES
from utils.calibration import detect_view, view_warning
from utils.drawing import draw_hud, draw_skeleton
from utils.heatmap import heatmap_chart
from utils.history import list_athletes, load_history, save_session
from utils.llm_summary import generate_summary
from utils.pdf_report import build_pdf
from utils.progress import (
    detect_personal_records, progress_notes, streak_days,
)
from utils.session_tracker import SessionTracker
from utils.tcx_export import build_tcx
from utils.voice import speak
from utils.workout import Phase, WorkoutPlan, WorkoutState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gymguru")

PROGRAMS_DIR = Path(__file__).resolve().parent / "programs"
REP_FLASH_SEC = 0.4
DROPOUT_SEC = 2.0          # warn if no pose detected for this long
PROCESS_WIDTH = 480         # downscale frames to this width before pose detection


# ---------------------------------------------------------------------------
# Video processor
# ---------------------------------------------------------------------------
class PoseProcessor:
    """Per-frame: pose → smoother → analyzer → HUD (+ bar path)."""

    def __init__(
        self, exercise_name: str, plan: WorkoutPlan,
        min_quality_score: float = 0.0, show_bar_path: bool = False,
        process_width: int = PROCESS_WIDTH, frame_skip: int = 0,
    ) -> None:
        self.detector = PoseDetector()
        self.smoother = LandmarkSmoother(alpha=0.6)
        self.exercise_name = exercise_name
        cls = EXERCISES[exercise_name]
        try:
            self.analyzer = cls(min_quality_score=min_quality_score)
        except TypeError:
            # Timed analyzers ignore the param.
            self.analyzer = cls()
        self.tracker = SessionTracker(exercise=exercise_name)
        self.workout = WorkoutState(plan=plan)
        self.bar_path = BarPathTracker(
            source="shoulders" if exercise_name == "Squat" else "wrists"
        )
        self.show_bar_path = show_bar_path
        self.process_width = int(process_width)
        self.frame_skip = max(0, int(frame_skip))
        self._frame_idx = 0
        self._cached_landmarks = None

        # Live state.
        self.last_score: float = 0.0
        self.last_feedback: list[str] = []
        self.last_grade: Optional[str] = None
        self.last_rep_number: int = 0
        self.last_rep_score: float = 0.0
        self.detected_view: str = "unknown"
        self._last_rep_at: float = 0.0
        self._last_pose_at: float = time.monotonic()

    def __del__(self) -> None:
        # Streamlit-webrtc creates a new processor on every config change;
        # the previous one is dereferenced. Make sure we release the native
        # MediaPipe landmarker so it doesn't leak C++ memory.
        try:
            self.detector.close()
        except Exception:
            pass

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        self.workout.tick()

        # ---- Downscale for pose detection, keep original for display. ----
        h0, w0 = img.shape[:2]
        if w0 > self.process_width:
            scale = self.process_width / w0
            small = cv2.resize(img, (self.process_width, int(h0 * scale)),
                               interpolation=cv2.INTER_AREA)
        else:
            small = img

        # ---- Frame skipping: reuse cached landmarks on skipped frames. ----
        self._frame_idx += 1
        run_detection = (self.frame_skip == 0) or (
            self._frame_idx % (self.frame_skip + 1) == 1
        )

        if run_detection:
            try:
                landmarks = self.detector.process(small)
            except Exception:
                logger.exception("Pose detection failed")
                landmarks = None
            self._cached_landmarks = landmarks
        else:
            landmarks = self._cached_landmarks

        if landmarks is None:
            dropout = None
            if time.monotonic() - self._last_pose_at > DROPOUT_SEC:
                dropout = "⚠ Pose lost — step back into frame"
            cv2.putText(img, "No pose detected", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 230), 2, cv2.LINE_AA)
            img = draw_hud(
                img, self.exercise_name, self.tracker.rep_count, self.last_score,
                unit=self.analyzer.unit.capitalize(),
                dropout_warning=dropout,
            )
            return av.VideoFrame.from_ndarray(img, format="bgr24")

        self._last_pose_at = time.monotonic()
        landmarks = self.smoother(landmarks)
        self.detected_view = detect_view(landmarks)
        warn = view_warning(self.detected_view, getattr(self.analyzer, "view_hint", "any"))

        unit_label = self.analyzer.unit.capitalize()
        target_per_set = self.workout.plan.reps_per_set

        if self.workout.phase == Phase.RESTING:
            img = draw_skeleton(img, landmarks, good_form=True)
            img = draw_hud(
                img, self.exercise_name, self.tracker.rep_count, self.last_score,
                feedback=["Resting — get ready"],
                set_idx=self.workout.current_set, total_sets=self.workout.plan.sets,
                target_reps=target_per_set,
                rest_remaining=self.workout.rest_remaining(),
                last_grade=self.last_grade, unit=unit_label,
                view_warning=warn, rejected_reps=self.analyzer.rejected_reps,
            )
            return av.VideoFrame.from_ndarray(img, format="bgr24")

        score, feedback, rep = self.analyzer.update(landmarks)
        self.tracker.log_frame(score, feedback)
        self.bar_path.update(landmarks)

        if rep is not None:
            self.tracker.log_rep(rep)
            self.last_grade = rep.grade
            self.last_rep_number = rep.rep_number
            self.last_rep_score = rep.score
            self._last_rep_at = time.monotonic()
            self.workout.on_rep(self.tracker.rep_count)
            logger.info("Rep %d  score=%.1f  grade=%s",
                        rep.rep_number, rep.score, rep.grade)

        self.last_score = score
        self.last_feedback = feedback

        rep_flash = (time.monotonic() - self._last_rep_at) < REP_FLASH_SEC
        img = draw_skeleton(img, landmarks, good_form=score >= 80)
        if self.show_bar_path:
            self.bar_path.draw(img)
        img = draw_hud(
            img, self.exercise_name, self.tracker.rep_count, score, feedback,
            set_idx=self.workout.current_set, total_sets=self.workout.plan.sets,
            target_reps=target_per_set, last_grade=self.last_grade,
            rep_flash=rep_flash, unit=unit_label, view_warning=warn,
            rejected_reps=self.analyzer.rejected_reps,
        )
        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ---------------------------------------------------------------------------
# Sidebar helpers
# ---------------------------------------------------------------------------
def _sidebar(athlete_history: list[dict]):
    with st.sidebar:
        st.header("Athlete")
        existing = list_athletes()
        choices = (existing or []) + ["+ New athlete"]
        chosen = st.selectbox("Profile", choices, index=0 if existing else 0)
        if chosen == "+ New athlete":
            athlete = st.text_input("New athlete name", value="default") or "default"
        else:
            athlete = chosen

        st.markdown("---")
        st.header("Workout")
        programs = load_programs(PROGRAMS_DIR)
        mode = st.radio("Mode", ["Single exercise", "Program"],
                        horizontal=True)

        if mode == "Program" and programs:
            program_name = st.selectbox("Program", list(programs.keys()))
            program = programs[program_name]
            st.caption(program.description)
            single_ex = None
            sets = reps = rest = None
        else:
            program = None
            single_ex = st.selectbox("Exercise", list(EXERCISES.keys()))
            sets = st.number_input("Sets", 1, 10, 3, 1)
            is_timed = EXERCISES[single_ex]().unit == "seconds"
            reps = st.number_input(
                "Seconds per hold" if is_timed else "Reps per set",
                1, 300, 30 if is_timed else 10, 1,
            )
            rest = st.number_input("Rest (seconds)", 0, 300, 60, 5)

        st.markdown("---")
        st.header("Coaching")
        voice_on = st.toggle("🔊 Voice cues", value=True)
        min_quality = st.slider(
            "Min form score to count rep",
            0, 90, 0, 5,
            help="Reps below this score are flagged as cheat reps and not counted.",
        )
        show_bar_path = st.toggle("📈 Show bar path trail", value=False)

        st.markdown("---")
        st.header("Performance")
        cam_res = st.selectbox(
            "Camera resolution",
            ["640×480", "854×480", "1280×720", "1920×1080"],
            index=0,
            help="Ask the webcam (e.g. DroidCam) to send lower res. "
                 "Lower = much less CPU.",
        )
        cam_fps = st.selectbox("Camera FPS", [10, 15, 20, 30], index=1)
        process_width = st.selectbox(
            "Processing width",
            [320, 480, 640, 960],
            index=1,
            help="Frames are downscaled to this width BEFORE pose detection. "
                 "Lower = faster, slightly less accurate.",
        )
        frame_skip = st.selectbox(
            "Detect every N frames", [1, 2, 3, 4], index=0,
            help="Reuse the last landmarks on skipped frames. "
                 "2 = run detection on half the frames, etc.",
        ) - 1

        st.markdown("---")
        st.caption(
            f"🔥 Streak: **{streak_days(athlete_history)}** day(s)"
        )
    return (athlete, program, single_ex, sets, reps, rest,
            voice_on, min_quality, show_bar_path,
            cam_res, cam_fps, process_width, frame_skip)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="GymGuru Coach", page_icon="💪", layout="wide")
    st.title("💪 GymGuru — Real-time AI Form Coach")

    # Load history for the current athlete early so sidebar can show streak.
    # We read athlete once with a placeholder, then re-read sidebar state.
    preview_athlete = st.session_state.get("athlete", "default")
    history = load_history(preview_athlete)

    (athlete, program, single_ex, sets, reps, rest,
     voice_on, min_quality, show_bar_path,
     cam_res, cam_fps, process_width, frame_skip) = _sidebar(history)
    st.session_state["athlete"] = athlete
    history = load_history(athlete)  # reload after choice

    # ---- Program runner state in session -----------------------------
    if program is not None:
        key = ("prog", athlete, program.name)
        if st.session_state.get("_prog_key") != key:
            st.session_state["_prog_runner"] = ProgramRunner(program)
            st.session_state["_prog_key"] = key
        runner: ProgramRunner = st.session_state["_prog_runner"]
        step = runner.current
        if step is None:
            st.success(f"🎉 Program **{program.name}** finished!")
            if st.button("Restart program"):
                runner.reset()
                st.rerun()
            return
        exercise = step.exercise
        plan = WorkoutPlan(sets=step.sets, reps_per_set=step.target, rest_sec=step.rest_sec)
        st.info(f"**Program:** {program.name} — step "
                f"{runner.step_index + 1}/{len(runner.program.steps)}: "
                f"{step.exercise} · {step.sets}×{step.target}")
    else:
        exercise = single_ex or "Squat"
        plan = WorkoutPlan(sets=int(sets or 3),
                           reps_per_set=int(reps or 10),
                           rest_sec=int(rest or 60))

    # ---- Video processor ---------------------------------------------
    def factory() -> PoseProcessor:
        return PoseProcessor(
            exercise_name=exercise, plan=plan,
            min_quality_score=float(min_quality),
            show_bar_path=show_bar_path,
            process_width=int(process_width),
            frame_skip=int(frame_skip),
        )

    # Parse "WxH" camera resolution into a getUserMedia constraint.
    w, h = (int(x) for x in cam_res.replace("×", "x").split("x"))
    video_constraints = {
        "width":  {"ideal": w, "max": w},
        "height": {"ideal": h, "max": h},
        "frameRate": {"ideal": int(cam_fps), "max": int(cam_fps)},
    }

    ctx = webrtc_streamer(
        key=f"gymguru-{exercise}-{plan.sets}-{plan.reps_per_set}-{plan.rest_sec}-{cam_res}-{cam_fps}",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=factory,
        media_stream_constraints={"video": video_constraints, "audio": False},
        async_processing=True,
    )

    if ctx.state.playing:
        st_autorefresh(interval=400, key="hud_refresh")

    proc: Optional[PoseProcessor] = ctx.video_processor if ctx else None  # type: ignore

    # ---- Live metrics ------------------------------------------------
    c1, c2, c3, c4, c5 = st.columns(5)
    if ctx.state.playing and proc is not None:
        unit = proc.analyzer.unit.capitalize()
        total_target = proc.workout.plan.sets * proc.workout.plan.reps_per_set
        c1.metric("Set", f"{proc.workout.current_set} / {proc.workout.plan.sets}")
        c2.metric(unit, f"{proc.tracker.rep_count} / {total_target}")
        c3.metric("Form (live)", f"{proc.last_score:0.0f}")
        c4.metric("Avg score", f"{proc.tracker.avg_rep_score:0.0f}")
        c5.metric("Last grade", proc.last_grade or "—")

        if voice_on and proc.last_rep_number > 0:
            msg = f"{proc.last_rep_number}, {proc.last_grade}"
            if proc.last_rep_score < 65 and proc.last_feedback:
                msg += ". " + proc.last_feedback[0]
            speak(msg, key=proc.last_rep_number)

        if proc.workout.phase == Phase.RESTING:
            rem = proc.workout.rest_remaining()
            st.warning(f"Resting — {rem}s remaining")
            # End-of-set debrief (#20).
            set_end = (proc.workout.current_set - 1) * proc.workout.plan.reps_per_set
            set_reps = [r for r in proc.tracker.reps if r.rep_number > set_end]
            if set_reps:
                avg = sum(r.score for r in set_reps) / len(set_reps)
                worst = min(set_reps, key=lambda r: r.score)
                st.info(
                    f"**Last set recap** — avg {avg:.0f}/100, "
                    f"worst rep #{worst.rep_number} ({worst.grade}). "
                    f"Top issue: {worst.feedback[0] if worst.feedback else '—'}"
                )
            # Pre-rep prompt (#19).
            if voice_on and rem in (3, 2, 1):
                speak(str(rem), key=f"countdown-{proc.workout.current_set}-{rem}")
        elif proc.workout.phase == Phase.DONE:
            st.success("🎉 Workout complete!")
            if voice_on:
                speak("Workout complete. Great job!", key="done")
            # Auto-advance to next program step.
            if program is not None:
                if st.button("Next exercise →"):
                    runner.advance()  # type: ignore[name-defined]
                    st.rerun()

        if proc.last_feedback:
            st.markdown("**Live feedback:** " + " · ".join(proc.last_feedback))
        if proc.detected_view != "unknown":
            hint = getattr(proc.analyzer, "view_hint", "any")
            ok = (hint == "any" or proc.detected_view == hint)
            st.caption(f"View: **{proc.detected_view}** — "
                       + ("✅ good" if ok else f"⚠️ prefer **{hint}** view"))
        if proc.analyzer.rejected_reps:
            st.caption(f"🚫 {proc.analyzer.rejected_reps} cheat rep(s) rejected this session")
    else:
        for c, label in zip((c1, c2, c3, c4, c5),
                            ("Set", "Reps", "Form", "Avg", "Grade")):
            c.metric(label, "—")
        st.info("Click **START** on the video widget above and allow webcam access.")

    # ---- Tabs: details / history / insights --------------------------
    tab_reps, tab_quality, tab_insights, tab_history = st.tabs(
        ["📊 Per-rep", "🤖 Quality", "💡 Insights", "📅 History"]
    )

    with tab_reps:
        if proc is not None and proc.tracker.reps:
            st.dataframe(
                [
                    {
                        "#": r.rep_number, "grade": r.grade,
                        "score": round(r.score, 1),
                        "min_angle": round(r.min_angle, 1),
                        "duration_s": round(r.duration_sec, 2),
                        "issues": "; ".join(r.feedback) or "—",
                    }
                    for r in proc.tracker.reps
                ],
                use_container_width=True,
            )
            # Bar path deviation diagnostic.
            if proc.bar_path.trail:
                st.caption(
                    f"Bar-path horizontal deviation: "
                    f"**{proc.bar_path.deviation_px(640):.1f} px** "
                    "(lower is straighter)"
                )
        else:
            st.caption("No reps yet.")

    with tab_quality:
        if proc is not None and len(proc.tracker.reps) >= 5:
            # Combine past reps across sessions of the same exercise.
            past_reps_features = []
            # We don't store full RepRecords per past session (summary only),
            # so we fit on the current session — still useful mid-session.
            clf = RepQualityClassifier().fit(proc.tracker.reps)
            if clf.is_ready:
                st.markdown("Reps flagged as anomalous vs your in-session median:")
                rows = []
                for r in proc.tracker.reps:
                    v = clf.classify(r)
                    if v.is_anomaly:
                        rows.append({"#": r.rep_number, "z": round(v.z, 2),
                                     "reason": v.reason,
                                     "score": round(r.score, 1)})
                if rows:
                    st.dataframe(rows, use_container_width=True)
                else:
                    st.success("No outlier reps detected — nice consistency.")
        else:
            st.caption("Needs at least 5 reps this session.")

    with tab_insights:
        st.markdown(f"**{athlete}** · streak: **{streak_days(history)}** day(s)")
        notes = progress_notes(history)
        if notes:
            st.markdown("### Recent trends")
            for n in notes:
                st.write(f"- {n.message}")
        if proc is not None and proc.tracker.reps:
            prs = detect_personal_records(history, proc.tracker.summary())
            if prs:
                st.markdown("### This session")
                for p in prs:
                    st.success(p.message)
        else:
            st.caption("Save a session to unlock PR detection.")

    with tab_history:
        if history:
            try:
                st.altair_chart(heatmap_chart(history), use_container_width=True)
            except Exception as e:
                st.caption(f"(Heatmap unavailable: {e})")
            st.dataframe(
                [
                    {"when": s.get("timestamp", "")[:16].replace("T", " "),
                     "exercise": s.get("exercise"),
                     "reps": s.get("reps", 0),
                     "avg_score": round(s.get("avg_rep_score", 0), 1)}
                    for s in history[::-1]
                ],
                use_container_width=True,
            )
        else:
            st.caption("No saved sessions yet for this athlete.")

    # ---- Session controls --------------------------------------------
    st.markdown("---")
    b1, b2, b3, b4, b5 = st.columns(5)

    if b1.button("End session & save"):
        if proc is None:
            st.warning("No active session.")
        else:
            summary = proc.tracker.summary()
            try:
                save_session(summary, athlete=athlete)
                st.success(f"Saved to {athlete}'s history.")
            except Exception as e:
                st.error(f"Could not save: {e}")
            # PRs + insights.
            for pr in detect_personal_records(history, summary):
                st.success(pr.message)
            # LLM summary (graceful fallback if no API key).
            with st.expander("🧠 Coach summary", expanded=True):
                st.markdown(generate_summary(
                    summary, [r.__dict__ for r in proc.tracker.reps]))
            st.json(summary)

    if proc is not None and proc.tracker.reps:
        slug = proc.exercise_name.lower().replace(" ", "_")
        b2.download_button(
            "CSV", data=proc.tracker.to_csv(),
            file_name=f"gymguru_{athlete}_{slug}.csv", mime="text/csv",
        )
        b3.download_button(
            "JSON", data=proc.tracker.to_json(),
            file_name=f"gymguru_{athlete}_{slug}.json", mime="application/json",
        )
        # PDF.
        try:
            pdf_bytes = build_pdf(
                athlete=athlete, summary=proc.tracker.summary(),
                reps=proc.tracker.reps,
            )
            b4.download_button(
                "PDF report", data=pdf_bytes,
                file_name=f"gymguru_{athlete}_{slug}.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            logger.warning("PDF generation failed: %s", e)
        # TCX.
        try:
            tcx = build_tcx(
                exercise=proc.exercise_name,
                started_at=datetime.fromtimestamp(proc.tracker.started_at),
                reps=proc.tracker.reps,
                duration_sec=proc.tracker.duration_sec,
                avg_score=proc.tracker.avg_rep_score,
            )
            b5.download_button(
                "TCX (Strava)", data=tcx,
                file_name=f"gymguru_{athlete}_{slug}.tcx",
                mime="application/vnd.garmin.tcx+xml",
            )
        except Exception as e:
            logger.warning("TCX generation failed: %s", e)

    with st.expander("ℹ️ How it works"):
        st.markdown(
            "**Pipeline:** MediaPipe Tasks (BlazePose, 33 landmarks) → EMA "
            "smoothing → form rules → hysteretic rep counter (or hold timer) → "
            "per-rep grade at deepest point → anomaly classifier flags cheat "
            "reps → workout programs sequence exercises.\n\n"
            "**Exports:** CSV / JSON / PDF report / TCX (Strava, Apple Health).\n\n"
            "**Optional:** set `OPENAI_API_KEY` for LLM coach summaries. "
            "Set `GYMGURU_POSE_MODEL=/app/models/pose_landmarker_heavy.task` "
            "for higher-accuracy pose tracking (costs CPU)."
        )


if __name__ == "__main__":
    main()
