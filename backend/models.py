from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from enum import Enum
import uuid

class Languages(str, Enum):
    EN = "en"
    ES = "es"
    CZ = "cz"

class ReflectionType(str, Enum):
    THOUGHT = "Thought"
    MEMORY = "Memory"
    LEARNING = "Learning"
    SUMMARY = "Summary"
    ASSUMPTION = "Assumption"
    BLIND_SPOT = "Blind Spot"
    CONTRADICTION = "Contradiction"

class SentimentType(str, Enum):
    POSITIVE = "Positive"
    SLIGHTLY_POSITIVE = "Slightly Positive"
    NEUTRAL = "Neutral"
    SLIGHTLY_NEGATIVE = "Slightly Negative"
    NEGATIVE = "Negative"

class User(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(min_length=1, max_length=200)
    prefered_language: Languages = Field(default=Languages.EN)

class Theme(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)

class Reflection(SQLModel, table=True):
    # Tree structure
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    user_id: str = Field(foreign_key="user.id")

    # Metadata
    language: Languages = Field(default=Languages.EN)
    type: ReflectionType = Field(default=ReflectionType.THOUGHT)
    sentiment: SentimentType = Field(default=SentimentType.NEUTRAL)
    context: Optional[str] = Field(default=None, max_length=500)
    
    # Q&A
    question: str = Field(min_length=1, max_length=200)
    answer: Optional[str] = Field(default=None, max_length=2000)

class ReflectionTheme(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    theme_id: str = Field(foreign_key="theme.id")
    reflection_id: str = Field(foreign_key="reflection.id")

class ReflectionHierarchy(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    child_id: str = Field(foreign_key="reflection.id")
    parent_id: str = Field(foreign_key="reflection.id") 