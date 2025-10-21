from enum import Enum
from typing import List
from pydantic import BaseModel

class SentimentType(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"

class QnAPair(BaseModel):
    id: str
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

class AnalysisResponse(BaseModel):
    # Tree structure
    id: str
    sentiment: SentimentType
    themes: List[str]

class FollowUpResponse(BaseModel):
    parent_id: str
    question: str
    context: str
