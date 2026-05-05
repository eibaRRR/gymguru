# GymGuru — Streamlit + MediaPipe on CPU
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps:
#   libgl1, libglib2.0-0  -> OpenCV runtime
#   libsm6, libxext6, libxrender1 -> OpenCV GUI libs that mediapipe links against
#   ffmpeg, libavdevice  -> PyAV / streamlit-webrtc
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxext6 \
      libxrender1 \
      ffmpeg \
      curl \
    && rm -rf /var/lib/apt/lists/*

# Download MediaPipe pose landmarker models. Lite is the default (fast on CPU).
# Set GYMGURU_POSE_MODEL=/app/models/pose_landmarker_heavy.task for higher accuracy.
RUN mkdir -p /app/models && \
    curl -fsSL -o /app/models/pose_landmarker_lite.task \
      https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task && \
    curl -fsSL -o /app/models/pose_landmarker_heavy.task \
      https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Optionally run tests at build time. Enable with:
#   docker build --build-arg RUN_TESTS=1 .
ARG RUN_TESTS=0
RUN if [ "$RUN_TESTS" = "1" ]; then python -m pytest tests/ -q; fi

EXPOSE 8501

# --server.address=0.0.0.0 so the container is reachable from the host.
CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
