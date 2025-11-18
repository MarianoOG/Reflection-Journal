FROM pytorch/pytorch:2.9.1-cuda12.6-cudnn9-runtime
RUN apt-get update && apt-get install -y python3 python3-venv ffmpeg && rm -rf /var/lib/apt/lists/*
ENV LD_LIBRARY_PATH=/opt/conda/lib:$LD_LIBRARY_PATH

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fastapi_app.py /app/fastapi_app.py

WORKDIR /app

EXPOSE 8080
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
