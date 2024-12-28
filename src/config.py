import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Settings
class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

