"""MediaPipe Pose wrapper using the Tasks API.

The legacy ``mediapipe.solutions.pose`` module is no longer shipped with
MediaPipe wheels on Python 3.12+, so we use ``mediapipe.tasks.vision``
which exposes the same 33 BlazePose landmarks via a downloadable
``pose_landmarker.task`` model.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
except ImportError as e:  # pragma: no cover - runtime dependency
    raise ImportError(
        "mediapipe is required. Install with `pip install mediapipe`."
    ) from e

logger = logging.getLogger(__name__)

# Default location for the pose landmarker model. Override with the
# ``GYMGURU_POSE_MODEL`` env var if you want to point at a different file.
DEFAULT_MODEL_PATH = os.environ.get(
    "GYMGURU_POSE_MODEL",
    str(Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_lite.task"),
)

# BlazePose landmark indices (same ordering as the legacy solutions API).
_LANDMARK_INDEX = {
    "nose": 0,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13,    "right_elbow": 14,
    "left_wrist": 15,    "right_wrist": 16,
    "left_hip": 23,      "right_hip": 24,
    "left_knee": 25,     "right_knee": 26,
    "left_ankle": 27,    "right_ankle": 28,
}
LANDMARK_NAMES: List[str] = list(_LANDMARK_INDEX.keys())

# Edges for skeleton drawing (kept here so utils/drawing can stay decoupled).
POSE_CONNECTIONS: List[Tuple[str, str]] = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
]


@dataclass
class Landmark:
    """A single landmark in normalized image coordinates."""
    x: float
    y: float
    z: float
    visibility: float

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


class PoseDetector:
    """Pose detector backed by ``mediapipe.tasks.vision.PoseLandmarker``."""

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        min_pose_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        min_pose_presence_confidence: float = 0.5,
    ) -> None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Pose landmarker model not found at {model_path}. "
                "Download it with: curl -L -o models/pose_landmarker_lite.task "
                "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
                "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
            )

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_pose_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            min_pose_presence_confidence=min_pose_presence_confidence,
            output_segmentation_masks=False,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)
        self._t0 = time.monotonic()
        # Connections expressed as friendly-name tuples for the drawing utils.
        self.pose_connections = POSE_CONNECTIONS

    def _now_ms(self) -> int:
        # Tasks API requires monotonically-increasing timestamps in VIDEO mode.
        return int((time.monotonic() - self._t0) * 1000.0)

    def process(self, image_bgr: np.ndarray) -> Optional[Dict[str, Landmark]]:
        """Detect pose on a BGR image and return a name->Landmark dict.

        Returns ``None`` when no pose is detected.
        """
        if image_bgr is None or image_bgr.size == 0:
            return None

        # Tasks API expects an mp.Image with SRGB data.
        rgb = np.ascontiguousarray(image_bgr[:, :, ::-1])
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        try:
            result = self._landmarker.detect_for_video(mp_image, self._now_ms())
        except Exception:
            logger.exception("PoseLandmarker.detect_for_video failed")
            return None

        if not result or not result.pose_landmarks:
            return None

        # ``pose_landmarks`` is a list-of-lists (one entry per detected pose).
        first = result.pose_landmarks[0]
        landmarks: Dict[str, Landmark] = {}
        for name, idx in _LANDMARK_INDEX.items():
            lm = first[idx]
            # Tasks API exposes ``visibility`` on NormalizedLandmark; fall back
            # to ``presence`` if not populated by the model.
            vis = float(getattr(lm, "visibility", 0.0) or getattr(lm, "presence", 0.0))
            landmarks[name] = Landmark(float(lm.x), float(lm.y), float(lm.z), vis)
        return landmarks

    def close(self) -> None:
        """Release the underlying landmarker."""
        try:
            self._landmarker.close()
        except Exception:  # pragma: no cover - best effort
            logger.exception("Failed to close PoseLandmarker")

    def __enter__(self) -> "PoseDetector":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
