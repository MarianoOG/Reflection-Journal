import os
from dotenv import load_dotenv

# Load environment variables from .env file
if os.path.exists(".env"):
    load_dotenv()

# Settings
class Settings:
    LLM_INFERENCE_URL: str = os.getenv("LLM_INFERENCE_URL", "")
    LLM_INFERENCE_API_KEY: str = os.getenv("LLM_INFERENCE_API_KEY", "")
    LLM_INFERENCE_MODEL_NAME: str = os.getenv("LLM_INFERENCE_MODEL_NAME", "") 
    
# Global settings
settings = Settings()
