import uuid
from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, Field
from enum import Enum

# Data Models

class Languages(Enum):
    EN = "en"
    ES = "es"
    

class ReflectionEntry(BaseModel):
    # Metadata
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = Field(default_factory=datetime.now)
    language: Languages = Field(default=Languages.EN)
    
    # Q&A
    question: str = Field(min_length=1, max_length=200)
    answer: Optional[str] = Field(default=None, max_length=2000)

    # Context
    context_type: Literal["Original", "Assumption", "Blind Spot", "Contradiction"] = Field(default="Original")
    context: Optional[str] = Field(default=None, max_length=500)

    # Analysis
    themes: List[str] = Field(default_factory=list)
    sentiment: Literal["Positive", "Slightly Positive", "Neutral", "Slightly Negative", "Negative"] = Field(default="Neutral")
    
    # Tree structure
    is_summary: bool = Field(default=False)
    parent_id: Optional[str] = Field(default=None)


class TaskEntry(BaseModel):
    # Metadata
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = Field(default_factory=datetime.now)
    language: Languages = Field(default=Languages.EN)

    # Task and importance
    task: str = Field(min_length=1, max_length=200)
    importance: Literal["High", "Medium", "Low"] = Field(default="Medium")

    # Tree structure
    is_done: bool = Field(default=False)
    parent_id: Optional[str] = Field(default=None)
    reflection_entry_id: Optional[str] = Field(default=None)

# LLM Models

class Belief(BaseModel):
    belief_type: Literal["Assumption", "Blind Spot", "Contradiction"]
    statement: str
    challenge_question: str

class ReflectionAnalysis(BaseModel):
    themes: List[str]
    sentiment: Literal["Positive", "Slightly Positive", "Neutral", "Slightly Negative", "Negative"]
    beliefs: List[Belief]

class Action(BaseModel):
    insight: str
    goal: str
    tasks: List[str]
    importance: Literal["High", "Medium", "Low"]

class ReportAnalysis(BaseModel):
    main_question: str
    answer_summary: str
    actions: List[Action]
