import uuid
from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

class Question(BaseModel):
    question: str = Field(min_length=1)
    weight: float = Field(ge=0, le=10)
    tags: List[str] = Field(min_length=1)

class Belief(BaseModel):
    belief_type: Literal["Assumption", "Blind Spot", "Contradiction"]
    statement: str
    challenge_question: str

class ReflectionAnalysis(BaseModel):
    themes: List[str]
    sentiment: Literal["Positive", "Slightly Positive", "Neutral", "Slightly Negative", "Negative"]
    beliefs: List[Belief]

class ReflectionEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = Field(default_factory=datetime.now)
    question: str = Field(min_length=1)
    answer: Optional[str] = None
    themes: List[str] = Field(default_factory=list)
    sentiment: Literal["Positive", "Slightly Positive", "Neutral", "Slightly Negative", "Negative"] = "Neutral"
    context_type: Literal["Original", "Assumption", "Blind Spot", "Contradiction"] = "Original"
    context: Optional[str] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)

class Insight(BaseModel):
    insight: str
    goal: str
    tasks: List[str]
    importance: Literal["High", "Medium", "Low"]

class ReportAnalysis(BaseModel):
    main_question: str
    answer_summary: str
    insights: List[Insight]

