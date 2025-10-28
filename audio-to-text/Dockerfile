FROM nvidia/cuda:13.0.1-cudnn-runtime-ubuntu24.04

RUN apt-get update && apt-get install -y python3 python3-venv ffmpeg && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Whisper models to avoid cold-start delays
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', device='cuda', compute_type='float16')"

COPY fastapi_app.py /app/fastapi_app.py

WORKDIR /app

EXPOSE 8080
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
