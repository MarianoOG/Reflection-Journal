import logging
import requests
from typing import Optional
from openai import OpenAI
from models import QnAPair, LLMSentiment, LLMThemes, LLMBeliefs
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


def sentiment_analysis(reflection: QnAPair) -> Optional[LLMSentiment]:
    """
    Analyze the sentiment of a reflection answer.
    Returns the emotional tone from positive to negative.
    """
    instructions = """
        Analyze the sentiment of the provided answer.
        Determine whether the overall tone is positive, negative, or neutral.
        Consider the emotional language, word choices, and overall mood expressed.
        Return the sentiment as one of: POSITIVE, NEGATIVE, NEUTRAL.
    """

    content = f"Question: {reflection.question}\nAnswer: {reflection.answer}\n"

    try:
        response = client.responses.parse(
            model=settings.LLM_INFERENCE_MODEL_NAME,
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": content}
            ],
            text_format=LLMSentiment,
            temperature=0.0,
            max_output_tokens=100,
            reasoning={"effort": "low"}
        )
    except Exception as e:
        logging.error(f"Error in sentiment_analysis: {str(e)}")
        return None
    return response.output_parsed


def themes_analysis(reflection: QnAPair) -> Optional[LLMThemes]:
    """
    Extract themes and general topics from a reflection answer.
    Returns a list of key topics the answer discusses.
    """
    instructions = """
        Extract the main themes and general topics from the provided answer.
        Identify key subjects, ideas, and domains that the answer talks about.
        Be concise with each theme - use 1-3 words per theme.
        Return a list of between 1 and 8 relevant themes.
    """

    content = f"Question: {reflection.question}\nAnswer: {reflection.answer}\n"

    try:
        response = client.responses.parse(
            model=settings.LLM_INFERENCE_MODEL_NAME,
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": content}
            ],
            text_format=LLMThemes,
            temperature=0.0,
            max_output_tokens=500,
            reasoning={"effort": "low"}
        )
    except Exception as e:
        logging.error(f"Error in themes_analysis: {str(e)}")
        return None
    return response.output_parsed


def beliefs_analysis(reflection: QnAPair) -> Optional[LLMBeliefs]:
    """
    Extract beliefs, assumptions, and blind spots from a reflection answer.
    Returns a list of beliefs with challenge questions to explore them deeper.
    """
    instructions = """
        Extract beliefs: assumptions, contradictions and blind spots from the provided answer.
        Identify underlying beliefs that the answer assumes or contradicts.
        For each belief, generate a challenge question that helps the user explore it deeper.
        Create open-ended, practical questions - avoid yes/no questions.
        Return a list of between 1 and 5 beliefs with their challenge questions.
    """

    content = f"Question: {reflection.question}\nAnswer: {reflection.answer}\n"

    try:
        response = client.responses.parse(
            model=settings.LLM_INFERENCE_MODEL_NAME,
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": content}
            ],
            text_format=LLMBeliefs,
            temperature=0.0,
            max_output_tokens=1500,
            reasoning={"effort": "medium"}
        )
    except Exception as e:
        logging.error(f"Error in beliefs_analysis: {str(e)}")
        return None
    return response.output_parsed
