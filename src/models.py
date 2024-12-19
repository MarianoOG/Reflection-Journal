import uuid
from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, Field
from enum import Enum

# Data Models

class Languages(Enum):
    EN = "en"
    ES = "es"

class QuestionEntry(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)
    language: Languages = Field(default=Languages.EN)
    weight: float = Field(ge=0, le=1, default=0.5)
    question: str = Field(min_length=1)
    context_type: Literal["Original", "Assumption", "Blind Spot", "Contradiction"] = Field(default="Original")
    context: Optional[str] = Field(default=None)

class ReflectionEntry(QuestionEntry):
    # Answer
    answer: Optional[str] = Field(default=None)
    # Analysis
    themes: List[str] = Field(default_factory=list)
    sentiment: Literal["Positive", "Slightly Positive", "Neutral", "Slightly Negative", "Negative"] = Field(default="Neutral")
    # Tree structure
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: Optional[str] = Field(default=None)
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
    importance: Literal["High", "Medium", "Low"]

class ReportAnalysis(BaseModel):
    main_question: str
    answer_summary: str
    insights: List[Insight]
