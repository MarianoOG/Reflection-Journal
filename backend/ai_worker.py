import logging
import requests
from config import settings


def ping_ai_worker() -> bool:
    """
    Ping the AI Worker service to check if it's available.

    Uses a 2-second timeout - enough for normal responses (<0.5s) plus
    network variance, but fails fast if service is cold (which takes ~3 minutes).
    The background keep-warm task will eventually catch the service when ready.

    Returns:
        bool: True if the service responds with 200 OK, False otherwise
    """
    try:
        response = requests.get(
            f'{settings.AI_WORKER_URL}/ping',
            headers={'accept': '*/*'},
            timeout=2
        )
        return response.status_code == 200
    except requests.exceptions.Timeout:
        logging.warning("AI Worker service ping timed out after 2s (service may be cold)")
        return False
    except Exception as e:
        logging.error(f"Error pinging AI Worker service: {e}")
        return False