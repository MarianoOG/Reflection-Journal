import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Settings
class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Directory Initializer
class DirectoryInitializer:
    reflections_dir = "../data/reflections/"
    reflection_summaries_dir = "../data/reflection_summaries/"
    reflection_insights_dir = "../data/reflection_insights/"

    def __init__(self):
        self.ensure_dir("../data/")
        self.ensure_dir(self.reflections_dir)
        self.ensure_dir(self.reflection_summaries_dir)
        self.ensure_dir(self.reflection_insights_dir)

    def ensure_dir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
