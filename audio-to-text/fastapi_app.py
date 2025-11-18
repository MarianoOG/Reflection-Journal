"""
Audio-to-Text Transcription Service

This FastAPI application provides speech-to-text transcription using OpenAI's Whisper model.
It includes API key authentication and multi-language support via faster-whisper.
"""

import logging
import os
from contextlib import asynccontextmanager
from io import BytesIO
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
import uvicorn
from dotenv import load_dotenv
from google.cloud import storage
from faster_whisper import WhisperModel
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# Environment Variables
load_dotenv()
DEVICE = os.environ.get("DEVICE")
PROJECT_NAME = os.environ.get("PROJECT_NAME")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "LOCAL")

# Initialize global variables
model = None
storage_client = None
bucket = None

# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Validate API key from request header.

    Ensures that incoming requests include a valid API key in the X-API-Key header
    for secure access to the transcription service.

    Args:
        api_key: The API key provided in the request header

    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API Key required. Please provide X-API-Key header."
        )

    if api_key != os.environ.get("AUDIO_TO_TEXT_API_KEY", ""):
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key"
        )

    return api_key


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Manage application lifespan events.

    On startup, initializes the Whisper model with appropriate device and compute type
    based on the MODEL_SIZE environment variable. Uses CUDA and float16 for large models,
    CPU and int8 for smaller models to optimize performance and memory usage.

    Also initializes the GCP storage client for accessing audio files from Cloud Storage.
    """
    global model, storage_client, bucket
    
    if ENVIRONMENT == 'PROD':
        model = WhisperModel("large-v3", device="cpu", compute_type="float16")
    else:
        model = WhisperModel("medium", device="cpu", compute_type="int8")
    
    # Initialize GCP storage client
    try:
        storage_client = storage.Client(project=PROJECT_NAME)
        bucket = storage_client.bucket(BUCKET_NAME)
    except Exception as e:
        logger.warning(f"Failed to initialize GCP storage client: {e}")

    yield


# Response model for transcription results
class TranscriptionResponse(BaseModel):
    """Response model for successful transcription."""
    detected_language: str
    language_probability: float
    transcription: str


app = FastAPI(lifespan=lifespan)
app.title = "Reflection Journal - Audio To Text"
app.version = "0.0.1"


@app.get(
    "/",
    tags=["Root"],
    summary="Welcome Endpoint",
    description="Returns a welcome message including the application title and version."
)
def root():
    """Root endpoint to verify the service is running."""
    return {"message": f"Welcome to {app.title} v{app.version}"}


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Checks if the model and GCP bucket are properly initialized."
)
def health():
    """
    Health check endpoint that verifies critical resources are available.

    Returns:
        dict: Contains a 'healthy' boolean and status of each service (model, bucket).
    """
    model_ready = model is not None
    bucket_ready = bucket is not None

    return {
        "healthy": model_ready and bucket_ready,
        "services": {
            "model": "available" if model_ready else "unavailable",
            "bucket": "available" if bucket_ready else "unavailable"
        }
    }


@app.post(
    "/transcribe",
    tags=["Transcription"],
    summary="Transcribe Audio to Text",
    description="Converts speech in audio files to text using faster-whisper. "
                "Reads audio files from GCP Cloud Storage and auto-detects language.",
    response_model=TranscriptionResponse,
    dependencies=[Security(verify_api_key)]
)
async def transcribe(audio_id: str):
    """
    Transcribe audio file from GCP Cloud Storage to text.

    Fetches an audio file from Cloud Storage (path: audio/{audio_id}) and converts it
    to text using the faster-whisper model. Automatically detects the language of the
    audio and returns the transcription along with language information.

    Args:
        audio_id: The identifier of the audio file in Cloud Storage (path: audio/{audio_id})

    Returns:
        TranscriptionResponse: Contains the transcribed text, detected language, and confidence

    Raises:
        HTTPException: 400 if audio_id is empty or model not initialized
        HTTPException: 404 if audio file not found in bucket
        HTTPException: 500 if transcription fails
        HTTPException: 401 if API key is invalid
    """
    if not model:
        raise HTTPException(
            status_code=500,
            detail="Whisper model not initialized. Please try again later."
        )

    if not audio_id or not audio_id.strip():
        raise HTTPException(
            status_code=400,
            detail="audio_id parameter is required and cannot be empty."
        )

    if not bucket:
        raise HTTPException(
            status_code=500,
            detail="GCP storage bucket not initialized. Please try again later."
        )

    try:
        # Construct the blob path
        blob_path = f"audio/{audio_id}"
        blob = bucket.blob(blob_path)

        # Check if blob exists
        if not blob.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Audio file not found: {blob_path}"
            )

        # Download file content to memory
        audio_content = blob.download_as_bytes()

        # Wrap in BytesIO for processing
        audio_bytes = BytesIO(audio_content)

        # Transcribe the audio from BytesIO
        segments, info = model.transcribe(audio_bytes, beam_size=5)

        # Aggregate transcription from all segments
        transcription = " ".join([segment.text.strip() for segment in segments])

        return {
            "detected_language": info.language,
            "language_probability": info.language_probability,
            "transcription": transcription
        }
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transcribe audio: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
