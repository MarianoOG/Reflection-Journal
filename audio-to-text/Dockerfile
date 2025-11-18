FROM python:3.12-slim
ARG ENVIRONMENT=LOCAL

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Preload the Whisper model during build to reduce cold start time
RUN if [ "$ENVIRONMENT" = "PROD" ]; then \
      python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', device='cpu', compute_type='int8')"; \
    else \
      python -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8')"; \
    fi

COPY fastapi_app.py /app/fastapi_app.py

EXPOSE 8080
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
