import json
import logging


class QuestionManager:
    user_id: str
    language: str
    file_path: str

    def __init__(self, user_id: str, language: str):
        self.user_id = user_id
        self.language = language
        if not self._user_exists(user_id):
            self._create_user(user_id, language)
    
    def _user_exists(self, user_id: str) -> bool:
        if user_id == "test":
            # TODO: create temporal file in memory
            return True
        # TODO: read from persistent database if exists return True
        return False

    def _create_user(self, user_id: str, language: str) -> None:
        # TODO: copy all questions from file (in language) to database to start the user collection
        file_path = f"questions_{language}.jsonl"
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    # TODO: insert question in database
                except Exception as e:
                    logging.error(e)
                    continue
        return None

    def get_question_by_id(self, entry_id: str) -> dict:
        # TODO: get question from database
        return {}

    def get_random_question(self) -> dict:
        # TODO: get random question from database
        return {}

    def add_question(self, question: str) -> bool:
        # TODO: insert question in database if it fails return False
        return True
    
    def delete_question_by_id(self, entry_id: str) -> bool:
        # TODO: delete question from database if it fails return False
        return False
