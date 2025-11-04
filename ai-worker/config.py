import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Load environment variables from .env file
if os.path.exists(".env"):
    load_dotenv()

# Settings
class Settings:
    LLM_INFERENCE_URL: str = os.getenv("LLM_INFERENCE_URL", "")
    LLM_INFERENCE_API_KEY: str = os.getenv("LLM_INFERENCE_API_KEY", "")
    LLM_INFERENCE_MODEL_NAME: str = os.getenv("LLM_INFERENCE_MODEL_NAME", "")
    AI_WORKER_API_KEY: str = os.getenv("AI_WORKER_API_KEY", "your-secret-key-change-this-in-production") 
    GOOGLE_CLOUD_PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "")
    PUB_SUB_TOPIC_ID: str = os.getenv("PUB_SUB_TOPIC_ID", "")

# Global settings
settings = Settings()
