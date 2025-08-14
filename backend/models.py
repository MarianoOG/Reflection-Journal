from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field
from enum import Enum
import uuid
import logging

####################
#    DB Models     #
####################

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
    id: str = Field(default_factory=lambda: "user_" + str(uuid.uuid4()), primary_key=True)
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=1, max_length=500, unique=True)
    password_hash: str = Field(min_length=1, max_length=255)
    prefered_language: Languages = Field(default=Languages.EN)
    last_login: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)

class Theme(SQLModel, table=True):
    id: str = Field(default_factory=lambda: "theme_" + str(uuid.uuid4()), primary_key=True)
    name: str = Field(min_length=1, max_length=200)

class Reflection(SQLModel, table=True):
    # Tree structure
    id: str = Field(default_factory=lambda: "reflection_" + str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    user_id: str = Field(foreign_key="user.id")
    parent_id: Optional[str] = Field(foreign_key="reflection.id", default=None)

    # Metadata
    language: Languages = Field(default=Languages.EN)
    type: ReflectionType = Field(default=ReflectionType.THOUGHT)
    sentiment: SentimentType = Field(default=SentimentType.NEUTRAL)
    context: Optional[str] = Field(default=None, max_length=500)
    
    # Q&A
    question: str = Field(min_length=1, max_length=200)
    answer: Optional[str] = Field(default=None, max_length=2000)

class ReflectionTheme(SQLModel, table=True):
    id: str = Field(default_factory=lambda: "reflection_theme_" + str(uuid.uuid4()), primary_key=True)
    theme_id: str = Field(foreign_key="theme.id")
    reflection_id: str = Field(foreign_key="reflection.id")

####################
#   DB Functions   #
####################

def create_db_and_tables(engine):
    logging.info("Creating database and tables...")
    try:
        SQLModel.metadata.create_all(engine)
        logging.info("Database and tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database and tables: {e}")
        raise

####################
#    LLM Models    #
####################

class LLMBelief(SQLModel):
    belief_type: ReflectionType
    statement: str
    challenge_question: str

class LLMEntryAnalysis(SQLModel):
    themes: List[str]
    sentiment: SentimentType
    beliefs: List[LLMBelief]

class LLMSummary(SQLModel):
    themes: List[str]
    sentiment: SentimentType
    main_question: str
    answer_summary: str

####################
#   Auth Models    #
####################

class UserCreate(SQLModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=1, max_length=500)
    password: str = Field(min_length=8, max_length=100)

class UserLogin(SQLModel):
    email: str = Field(min_length=1, max_length=500)
    password: str = Field(min_length=1, max_length=100)

class Token(SQLModel):
    access_token: str
    token_type: str

class UserResponse(SQLModel):
    id: str
    name: str
    email: str
    prefered_language: Languages
    last_login: datetime
    created_at: datetime