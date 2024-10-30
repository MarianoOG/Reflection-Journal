import requests
from ..core.config import settings

class TodoistService:
    def __init__(self):
        self.api_key = settings.TODOIST_API_KEY
        self.base_url = "https://api.todoist.com/rest/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_task(self, content, due_date=None):
        endpoint = f"{self.base_url}/tasks"
        payload = {"content": content}
        if due_date:
            payload["due_date"] = due_date
        
        response = requests.post(endpoint, headers=self.headers, json=payload)
        return response.json()
