import logging
import requests
from typing import Optional, List
from openai import OpenAI
from models import QnAPair, LLMEntryAnalysis, LLMSummary
from config import settings

# Initialize OpenAI client with vLLM compatible endpoint
client = OpenAI(
    base_url=settings.LLM_INFERENCE_URL + "/v1",
    api_key=settings.LLM_INFERENCE_API_KEY
)


def ping_llm() -> bool:
    """
    Ping the LLM inference service to check if it's available.

    Uses a 2-second timeout - enough for normal responses (<0.5s) plus
    network variance, but fails fast if service is cold (which takes ~3 minutes).
    The background keep-warm task will eventually catch the service when ready.

    Returns:
        bool: True if the service responds with 200 OK, False otherwise
    """
    try:
        response = requests.get(
            f'{settings.LLM_INFERENCE_URL}/ping',
            headers={'accept': '*/*'},
            timeout=2
        )
        return response.status_code == 200
    except requests.exceptions.Timeout:
        logging.warning("LLM service ping timed out after 2s (service may be cold)")
        return False
    except Exception as e:
        logging.error(f"Error pinging LLM service: {e}")
        return False


def analyze_reflection(reflection: QnAPair) -> Optional[LLMEntryAnalysis]:
    # Instructions for the LLM
    instructions = """
        Extract information from the reflection and provide a detailed analysis.
        The analysis will include a list of general topics that the answer talks about.
        It will include the sentiment of the answer from positive to negative.
        It will include a list of beliefs or blind spots that the answer assumes or contradicts.
        The list of beliefs should be between 1 and 5 beliefs.
        Each belief will have a challenge question that will help the user to understand the belief better and explore it deeper.
        Create open questions and avoid yes or no questions, use questions that are practical and useful.
    """

    content = f"Question: {reflection.question}\nAnswer: {reflection.answer}\n"

    try:
        response = client.responses.parse(
            model=settings.LLM_INFERENCE_MODEL_NAME,
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": content}
            ],
            text_format=LLMEntryAnalysis,
            temperature=0.0,
            max_output_tokens=2000,
            reasoning={ "effort": "high" }
        )
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return None
    return response.output_parsed


def summarize_reflections(reflections: List[QnAPair]) -> Optional[LLMSummary]:
    instructions = """
        You will analyze a report of questions and answers from a reflection journal.
        The main question will be the question that the report is related to.
        The answer summary will be an overall answer of the main question of the report with the main points.
        The insights will be a list of insights on the core beliefs and assumptions that the report provides.
        The goal will be a short description of the goal that the report is related to based on the insights.
        The tasks will be a long a detail list of tasks from start to finish that I can do to archive the goal in the shortest time possible.
        The importance of the tasks will be a rating of the tasks from high to low based on the insights.
    """

    if reflections is None or len(reflections) == 0:
        return None

    report = "\n".join([f"Question: {reflection.question}\nAnswer: {reflection.answer}\n" for reflection in reflections])

    try:
        response = client.responses.parse(
            model=settings.LLM_INFERENCE_MODEL_NAME,
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": report}
            ],
            text_format=LLMSummary,
            temperature=0.0,
            max_output_tokens=2000,
            reasoning={ "effort": "high" }
        )
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return None
    return response.output_parsed
