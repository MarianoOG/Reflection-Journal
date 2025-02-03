import logging
import random
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, create_engine, Session, select
from enum import Enum
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import uvicorn
from config import Settings
import uuid

settings = Settings()
database_engine = None

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

def create_db_and_tables(engine):
    logging.info("Creating database and tables...")
    try:
        SQLModel.metadata.create_all(engine)
        logging.info("Database and tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database and tables: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    global database_engine
    database_engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False}, echo=True)
    create_db_and_tables(database_engine)
    yield
    # Shutdown
    database_engine.dispose()

app = FastAPI(lifespan=lifespan)
app.title = "Reflexion Journal"
app.version = "0.0.1"


@app.get("/health")
def health_check():
    """
    Health endpoint to check database connection.
    """
    try:
        with Session(database_engine) as session:
            session.exec(select(User))
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database connection failed")


@app.get("/")
def root():
    return {"message": f"Welcome to {app.title} v{app.version}"}


# class ReflectionManager:
#     user_id: str
#     reflection_entries: Dict[str, Reflection]

#     def __init__(self, user_id: str):
#         self.user_id = user_id
#         self.reflection_entries = {}

#     def upsert_reflection(self, reflection_entry: Reflection) -> bool:
#         if not self.original_entry_id:
#             self.original_entry_id = reflection_entry.id
#         self.reflection_entries[reflection_entry.id] = reflection_entry
#         return True
    
#     def load_reflections(self, file_path: str) -> None:
#         with open(file_path, "r", encoding="utf-8") as f:
#             for line in f:
#                 try:
#                     data = json.loads(line)
#                     current_entry = Reflection(**data)
#                 except Exception as e:
#                     logging.error(e)
#                     continue
#                 self.upsert_reflection(current_entry)

#     def get_reflection_by_id(self, reflection_id: str) -> Optional[Reflection]:
#         return self.reflection_entries.get(reflection_id)
    
#     def get_parent_by_id(self, reflection_id: str) -> Optional[Reflection]:
#         if reflection_id in self.reflection_entries:
#             parent_id = self.reflection_entries[reflection_id].parent_id
#             if parent_id:
#                 return self.get_reflection_by_id(parent_id)
#         return None

#     def get_children_by_id(self, reflection_id: str) -> List[Reflection]:
#         children = []
#         # TODO: get children from database
#         return children
    
#     def get_unanswered_reflection_entry(self) -> Optional[Reflection]:
#         unanswered_entries = [entry for entry in self.reflection_entries.values() if not entry.answer]
#         if unanswered_entries:
#             return random.choice(unanswered_entries)
#         return None
    
#     def get_language_by_id(self, reflection_id: str) -> Languages:
#         if reflection_id in self.reflection_entries:
#             return self.reflection_entries[reflection_id].language
#         return Languages.EN

#     def delete_reflection_by_id(self, reflection_id: str) -> bool:
#         if reflection_id in self.reflection_entries:
#             # Remove the reflection from the parent
#             parent = self.get_parent_by_id(reflection_id)
#             if parent:
#                 # TODO: Remove the reflection from the parent
#                 pass
            
#             # Remove the reflection from the children
#             children = self.get_children_by_id(reflection_id)
#             for child in children:
#                 if parent:
#                     child.parent_id = parent.id
#                     # TODO: Add the reflection to the parent
#                     pass
#                 else:
#                     self.delete_reflection_by_id(child.id)

#             # Remove the reflection from the entries
#             del self.reflection_entries[reflection_id]

#             # Remove the reflection from the original entry
#             if self.original_entry_id == reflection_id:
#                 self.original_entry_id = None
#                 self.reflection_entries = {}

#             return True
#         return False

#     def analyze_reflection_by_id(self, reflection_id: str) -> bool:
#         # Get the entry and check if it exists
#         reflection = self.get_reflection_by_id(reflection_id)
#         if not reflection or not reflection.answer:
#             logging.warning("Reflection not found or answer not set")
#             return False

#         # Analyze the reflection
#         analysis = analyze_reflection(reflection.question, reflection.answer, reflection.language.value)
#         if not analysis:
#             logging.warning("Analysis not generated")
#             return False
        
#         # Set the themes and sentiment
#         reflection.themes = analysis.themes
#         reflection.sentiment = analysis.sentiment

#         # Create the children entries
#         for belief in analysis.beliefs:
#             new_reflection = Reflection(
#                 question=belief.challenge_question, 
#                 context=belief.statement, 
#                 context_type=belief.belief_type,
#                 parent_id=reflection.id,
#                 language=reflection.language
#             )
#             self.upsert_reflection(new_reflection)
#             reflection.children_ids.append(new_reflection.id)
#         return True

#     def analyze_all_reflections(self) -> None:
#         for reflection in self.reflection_entries.values():
#             self.analyze_reflection_by_id(reflection.id)

#     def _get_recursive_report(self, entry_id: str, prefix: str = "# ") -> str:
#         # Get the entry and check if it exists and has an answer
#         entry = self.get_reflection_by_id(entry_id)
#         if not entry or not entry.answer:
#             return ""
        
#         # Generate the string
#         text = f"{prefix}{entry.question}\n\n"
#         if entry.context:
#             text += f"**{entry.context_type}**: {entry.context}\n\n"
#         text += f"{entry.answer}\n\n"

#         # Recursively get the children strings
#         for child in self.get_children_by_id(entry_id):
#             text += self._get_recursive_report(child.id, f"#{prefix} ")
#         return text
    
#     def get_report(self) -> str:
#         if not self.original_entry_id:
#             return ""
#         return self._get_recursive_report(self.original_entry_id)
    
#     def get_statistics(self) -> tuple[int, int]:
#         analyzed_entries = len([entry for entry in self.reflection_entries.values() if entry.themes])
#         return analyzed_entries, len(self.reflection_entries)
    
# class InsightsManager:
#     uuid_str: str
#     reflection_manager: ReflectionManager
#     summary_entry: Optional[Reflection]
#     insights: List[Insight]

#     def __init__(self, reflection_manager: ReflectionManager):
#         self.uuid_str = uuid4().hex
#         self.reflection_manager = reflection_manager
#         self.insights = []
#         self.summary_entry = None
    
#     def get_summary_entry(self) -> Optional[Reflection]:
#         return self.summary_entry
    
#     def get_insights(self) -> List[Insight]:
#         return self.insights

#     def _generate_insights(self) -> bool:
#         # Get the report
#         report = self.reflection_manager.get_report()
#         if not report:
#             return False
        
#         # Analyze the report
#         language = self.reflection_manager.get_language()
#         analysis = analyze_report(report, language.value)
#         if not analysis:
#             return False
        
#         # Create the summary entry and insights
#         reflection_analysis = analyze_reflection(analysis.main_question, analysis.answer_summary, language.value)
#         if not reflection_analysis:
#             return False
        
#         self.summary_entry = Reflection(
#             question=analysis.main_question,
#             answer=analysis.answer_summary,
#             language=language,
#             sentiment=reflection_analysis.sentiment,
#             context='\n'.join([belief.belief_type + ': ' + belief.statement for belief in reflection_analysis.beliefs]),
#         )
#         self.insights = analysis.insights
#         return True

#     def save_journal_entry(self) -> bool:
#         if not self._generate_journal_entry():
#             logging.error("Journal entry not generated")
#             return False
        
#         now = datetime.now()
#         # TODO: develop in sqllite, Save reflections
#         # TODO: develop in sqllite, Save summary
#         # TODO: develop in sqllite, Save insights
#         # TODO: develop in sqllite, Save tags?
#         return True


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
