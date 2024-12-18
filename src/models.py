import uuid
from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

# Data Models

class QuestionEntry(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)
    lang: Literal["en", "es"] = "en"
    weight: float = Field(ge=0, le=1, default=0.5)
    question: str = Field(min_length=1)

class ReflectionEntry(QuestionEntry):
    # Answer
    answer: Optional[str] = None
    # Analysis
    themes: List[str] = Field(default_factory=list)
    sentiment: Literal["Positive", "Slightly Positive", "Neutral", "Slightly Negative", "Negative"] = "Neutral"
    context_type: Literal["Original", "Assumption", "Blind Spot", "Contradiction"] = "Original"
    context: Optional[str] = None
    # Tree structure
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)

# LLM Models

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
    themes: List[str]
    importance: Literal["High", "Medium", "Low"]

class ReportAnalysis(BaseModel):
    main_question: str
    answer_summary: str
    insights: List[Insight]
