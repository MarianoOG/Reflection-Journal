from enum import Enum
from typing import Optional, List
from config import Settings
import logging
from openai import OpenAI
from pydantic import BaseModel

settings = Settings()

# Initialize OpenAI client with vLLM compatible endpoint
client = OpenAI(
    base_url=settings.LLM_INFERENCE_URL,
    api_key=settings.LLM_INFERENCE_API_KEY
)


####################
#    LLM Models    #
####################

class SentimentType(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"

class QnAPair(BaseModel):
    question: str
    answer: str

class LLMBelief(BaseModel):
    statement: str
    challenge_question: str

class LLMEntryAnalysis(BaseModel):
    themes: List[str]
    sentiment: SentimentType
    beliefs: List[LLMBelief]

class LLMSummary(BaseModel):
    main_question: str
    answer_summary: str


####################
#   LLM Functions  #
####################


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
            max_output_tokens=1000,
            reasoning={ "effort": "low" }
        )
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return None
    return response.output_parsed


####################
#      Testing     #
####################

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Test 1: analyze_reflection
    print("\n" + "="*50)
    print("Testing analyze_reflection")
    print("="*50)

    test_reflection = QnAPair(
        question="What am I most grateful for today?",
        answer="""I'm grateful for the conversation I had with my mentor today.
        They helped me realize that I've been procrastinating on my project because
        I'm afraid of failure. I always assumed that being busy meant I was being productive,
        but that's not always true. I need to focus on what truly matters."""
    )

    analysis = analyze_reflection(test_reflection)
    if analysis:
        print(f"\nThemes: {analysis.themes}")
        print(f"Sentiment: {analysis.sentiment}")
        print(f"\nBeliefs ({len(analysis.beliefs)} found):")
        for i, belief in enumerate(analysis.beliefs, 1):
            print(f"\n{i}. Statement: {belief.statement}")
            print(f"   Challenge: {belief.challenge_question}")
    else:
        print("Analysis failed!")

    # Test 2: summarize_reflections
    print("\n" + "="*50)
    print("Testing summarize_reflections")
    print("="*50)

    test_reflections = [
        QnAPair(
            question="What did I learn from today's challenge?",
            answer="I learned that asking for help is not a weakness. When I finally asked my colleague for assistance, we solved the problem in 30 minutes instead of me struggling alone for hours."
        ),
        QnAPair(
            question="What assumption did I challenge today?",
            answer="I challenged my assumption that I need to know everything before starting. I started the project with incomplete knowledge and learned as I went."
        ),
        QnAPair(
            question="What would I do differently?",
            answer="I would reach out for help sooner and not wait until I'm completely stuck. Collaboration makes everything easier."
        )
    ]

    summary = summarize_reflections(test_reflections)
    if summary:
        print(f"\nMain Question: {summary.main_question}")
        print(f"\nAnswer Summary: {summary.answer_summary}")
    else:
        print("Summary failed!")

    print("\n" + "="*50)
    print("Testing completed!")
    print("="*50)
