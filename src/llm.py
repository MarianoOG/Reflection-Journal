from typing import Optional, Literal, List
from pydantic import BaseModel
from openai import OpenAI
from config import settings

######################
# LLM Response Models
######################


class Belief(BaseModel):
    belief_type: Literal["Assumption", "Blind Spot", "Contradiction"]
    statement: str
    challenge_question: str

class ReflectionAnalysis(BaseModel):
    themes: List[str]
    sentiment: Literal["Positive", "Slightly Positive", "Neutral", "Slightly Negative", "Negative"]
    beliefs: List[Belief]

class Insight(BaseModel):
    insight: str
    goal: str
    tasks: List[str]
    importance: Literal["High", "Medium", "Low"]

class ReportAnalysis(BaseModel):
    main_question: str
    answer_summary: str
    insights: List[Insight]


######################
# LLM Service
######################


client = OpenAI(api_key=settings.OPENAI_API_KEY)
        

def analyze_reflection(question: str, answer: str) -> Optional[ReflectionAnalysis]:        
    instructions = "Extract information from the reflection and provide a detailed analysis."
    instructions += "The analysis will include a list of general topics that the answer talks about."
    instructions += "It will include the sentiment of the answer from positive to negative."
    instructions += "It will include a list of beliefs or blind spots that the answer assumes or contradicts."
    content = f"Question: {question}\n"
    content += f"Answer: {answer}\n"
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": content},
            ],
            response_format=ReflectionAnalysis,
            temperature=0.0,
            max_tokens=3000
        )
    except Exception as e:
        print(e)
        return None
    return completion.choices[0].message.parsed


def analyze_report(report: str) -> Optional[ReportAnalysis]:
    instructions = "You will analyze a report of questions and answers from a reflection journal."
    instructions += "The main question will be the question that the report is related to."
    instructions += "The answer summary will be an overall answer of the main question of the report with the main points."
    instructions += "The insights will be a list of insights on the core beliefs and assumptions that the report provides."
    instructions += "The goal will be a short description of the goal that the report is related to based on the insights."
    instructions += "The tasks will be a long a detail list of tasks from start to finish that I can do to archive the goal in the shortest time possible."
    instructions += "The importance of the tasks will be a rating of the tasks from high to low based on the insights."
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": report},
            ],
            response_format=ReportAnalysis,
            temperature=0.0,
            max_tokens=3000
        )
    except Exception as e:
        print(e)
        return None
    return completion.choices[0].message.parsed
