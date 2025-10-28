FROM nvidia/cuda:13.0.1-cudnn-runtime-ubuntu24.04

RUN apt-get update && apt-get install -y python3 python3-pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build argument to specify which model to download (defaults to "small" for local dev)
ARG WHISPER_MODELS="small"

# Pre-download Whisper models to avoid cold-start delays
RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODELS}')"

COPY fastapi_app.py /app/fastapi_app.py

WORKDIR /app

EXPOSE 8080
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
