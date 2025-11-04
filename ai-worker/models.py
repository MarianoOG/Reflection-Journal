from enum import Enum
from typing import List
from pydantic import BaseModel


class QnAPair(BaseModel):
    id: str
    question: str
    answer: str

class LLMQuestion(BaseModel):
    question: str

class SentimentType(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"

class LLMSentiment(BaseModel):
    sentiment: SentimentType

class LLMThemes(BaseModel):
    themes: List[str]

class Belief(BaseModel):
    statement: str
    challenge_question: str

class LLMBeliefs(BaseModel):
    beliefs: List[Belief]

class AnalysisResponse(BaseModel):
    question: str
    sentiment: SentimentType
    themes: List[str]
