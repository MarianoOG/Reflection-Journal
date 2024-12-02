import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Settings
class Settings:
    TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Directory Initializer
class DirectoryInitializer:
    def __init__(self):
        self.ensure_dir("../data/")
        self.ensure_dir(f"../data/insights/")
        self.ensure_dir(f"../data/reflections/")

    def ensure_dir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

# Initialize settings and directory
settings = Settings()
directory_initializer = DirectoryInitializer()
