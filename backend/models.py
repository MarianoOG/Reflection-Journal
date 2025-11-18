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

class SentimentType(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
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
    user_id: str = Field(foreign_key="user.id")

class Reflection(SQLModel, table=True):
    # Tree structure
    id: str = Field(default_factory=lambda: "reflection_" + str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    user_id: str = Field(foreign_key="user.id")
    parent_id: Optional[str] = Field(foreign_key="reflection.id", default=None)

    # Metadata
    language: Languages = Field(default=Languages.EN)
    sentiment: SentimentType = Field(default=SentimentType.NEUTRAL)
    context: Optional[str] = Field(default=None, max_length=500)
    
    # Q&A
    question: str = Field(min_length=1, max_length=200)
    answer: Optional[str] = Field(default=None, max_length=2000)

class ReflectionTheme(SQLModel, table=True):
    id: str = Field(default_factory=lambda: "reflection_theme_" + str(uuid.uuid4()), primary_key=True)
    theme_id: str = Field(foreign_key="theme.id")
    reflection_id: str = Field(foreign_key="reflection.id")

class GoalType(str, Enum):
    BOOLEAN = "boolean"
    METRIC = "metric"

class GoalStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

class ConfidenceLevel(str, Enum):
    VERY_CONFIDENT = "very_confident"
    CONFIDENT = "confident"
    MODERATELY_CONFIDENT = "moderately_confident"
    SLIGHTLY_CONFIDENT = "slightly_confident"
    NOT_CONFIDENT = "not_confident"

class Goal(SQLModel, table=True):
    __tablename__ = "goals"

    id: str = Field(default_factory=lambda: "goal_" + str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)

    # SMART: Specific
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)

    # SMART: Measurable
    goal_type: GoalType = Field(...)

    # For metric goals (track progress)
    target_value: Optional[float] = None
    current_value: Optional[float] = Field(default=0.0)
    unit: Optional[str] = Field(default=None, max_length=50)  # e.g., "kg", "posts", "hours"

    # SMART: Achievable - Track confidence changes
    initial_confidence: Optional[ConfidenceLevel] = None  # Set at creation
    current_confidence: Optional[ConfidenceLevel] = None  # Updated as things change

    # SMART: Relevant
    justification: Optional[str] = Field(default=None, max_length=500)

    # SMART: Time-bound
    deadline: Optional[datetime] = None

    # Ordering & Priority
    priority: int = Field(default=1000)  # Gap-based ordering per user

    # Status Tracking
    status: GoalStatus = Field(default=GoalStatus.NOT_STARTED)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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
#   Auth Models    #
####################

class UserCreate(SQLModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=1, max_length=500)
    password: str = Field(min_length=8, max_length=32)

class UserLogin(SQLModel):
    email: str = Field(min_length=1, max_length=500)
    password: str = Field(min_length=8, max_length=32)

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

class UserUpdate(SQLModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    prefered_language: Optional[Languages] = None

####################
# Dashboard Models #
####################

class UserStats(SQLModel):
    total_entries: int
    entries_with_answers: int
    follow_up_questions_without_answers: int

class SentimentByDate(SQLModel):
    date: str  # YYYY-MM-DD format
    sentiment_value: float  # Average sentiment (-1 to 1)
    entries_count: int  # Number of entries on that day

class UserSentimentData(SQLModel):
    sentiment_data: List[SentimentByDate]
