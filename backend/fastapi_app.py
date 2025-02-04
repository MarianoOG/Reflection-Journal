# Standard library imports
import random
import uuid
from contextlib import asynccontextmanager
import json

# Third-party imports
from fastapi import FastAPI, HTTPException
from sqlmodel import Session, create_engine, select, func
import uvicorn

# Local application imports
from config import Settings
from llm import analyze_reflection
from models import User, Theme, Reflection, ReflectionTheme, ReflectionType, create_db_and_tables

settings = Settings()
database_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    global database_engine
    database_engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    create_db_and_tables(database_engine)
    yield
    # Shutdown
    database_engine.dispose()

app = FastAPI(lifespan=lifespan)
app.title = "Reflexion Journal"
app.version = "0.0.1"


@app.get("/themes")
def list_themes(offset: int = 0, limit: int = 100):
    """
    List themes with pagination.
    
    Args:
        offset (int): Number of records to skip (default: 0)
        limit (int): Maximum number of records to return (default: 10, max: 100)
    """
    if limit > 100:
        limit = 100
    
    with Session(database_engine) as session:
        themes = session.exec(select(Theme).offset(offset).limit(limit)).all()
        return themes

@app.get("/themes/{theme_id}/reflections")
def get_theme_reflections(theme_id: str):
    """
    Retrieve all reflections associated with a given theme ID.
    
    Args:
        theme_id (str): The ID of the theme
    """
    with Session(database_engine) as session:
        # Verify theme exists
        theme = session.get(Theme, theme_id)
        if not theme:
            raise HTTPException(status_code=404, detail="Theme not found")
        
        # Get all reflection relations for this theme
        reflection_relations = session.exec(
            select(ReflectionTheme).where(ReflectionTheme.theme_id == theme_id)
        ).all()
        
        # Get all reflections
        reflections = dict()
        for relation in reflection_relations:
            reflection = session.get(Reflection, relation.reflection_id)
            if reflection:
                reflections[reflection.id] = reflection
        
        return list(reflections.values())

@app.delete("/themes/{theme_id}")
def delete_theme(theme_id: str):
    """
    Delete a theme by ID and all its relations in ReflectionTheme.
    """
    with Session(database_engine) as session:
        theme = session.get(Theme, theme_id)
        if not theme:
            raise HTTPException(status_code=404, detail="Theme not found")
        
        # Delete all ReflectionTheme relations for this theme
        reflection_themes = session.exec(select(ReflectionTheme).where(ReflectionTheme.theme_id == theme_id)).all()
        for relation in reflection_themes:
            session.delete(relation)
        
        # Delete the theme itself
        session.delete(theme)
        session.commit()
        return {"message": "Theme and its relations deleted successfully"}

@app.get("/reflections")
def list_reflections(offset: int = 0, limit: int = 100):
    """
    List reflections with pagination.
    
    Args:
        offset (int): Number of records to skip (default: 0)
        limit (int): Maximum number of records to return (default: 100, max: 100)
    """
    if limit > 100:
        limit = 100
    
    with Session(database_engine) as session:
        reflections = session.exec(select(Reflection).offset(offset).limit(limit)).all()
        return reflections

@app.put("/reflections/")
def upsert_reflection(reflection: Reflection):
    """
    Upsert a reflection. If reflection_id exists, update it; if not, create new with specified ID.
    """
    with Session(database_engine) as session:
        existing_reflection = session.get(Reflection, reflection.id)
        if existing_reflection:
            existing_reflection.parent_id = reflection.parent_id
            existing_reflection.language = reflection.language
            existing_reflection.type = reflection.type
            existing_reflection.sentiment = reflection.sentiment
            existing_reflection.context = reflection.context
            existing_reflection.question = reflection.question
            existing_reflection.answer = reflection.answer
        else:
            session.add(reflection)
        session.commit()
        session.refresh(existing_reflection if existing_reflection else reflection)
        return existing_reflection if existing_reflection else reflection

@app.get("/reflections/{reflection_id}")
def get_reflection(reflection_id: str):
    """
    Retrieve a reflection by ID.
    """
    with Session(database_engine) as session:
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        return reflection

@app.get("/reflections/{reflection_id}/parent")
def get_reflection_parent(reflection_id: str):
    """
    Retrieve the parent reflection of a given reflection ID.
    """
    with Session(database_engine) as session:
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        if not reflection.parent_id:
            return None
            
        parent = session.get(Reflection, reflection.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent reflection not found")
        return parent

@app.get("/reflections/{reflection_id}/children")
def get_reflection_children(reflection_id: str):
    """
    Retrieve all child reflections of a given reflection ID.
    """
    with Session(database_engine) as session:
        # First verify the parent reflection exists
        parent = session.get(Reflection, reflection_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Reflection not found")
            
        children = session.exec(
            select(Reflection).where(Reflection.parent_id == reflection_id)
        ).all()
        return children

@app.get("/reflections/{reflection_id}/themes")
def get_reflection_themes(reflection_id: str):
    """
    Retrieve all themes associated with a given reflection ID.
    
    Args:
        reflection_id (str): The ID of the reflection
    """
    with Session(database_engine) as session:
        # Verify reflection exists
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        # Get all theme relations for this reflection
        reflection_themes = session.exec(
            select(ReflectionTheme).where(ReflectionTheme.reflection_id == reflection_id)
        ).all()
        
        # Get all themes
        themes = []
        for relation in reflection_themes:
            theme = session.get(Theme, relation.theme_id)
            if theme:
                themes.append(theme)
        
        return themes

@app.post("/reflections/{reflection_id}/analyze")
def analyze_reflection_by_id(reflection_id: str):
    """
    Analyze a reflection by ID using LLM and update the reflection with the analysis results.
    
    Args:
        reflection_id (str): The ID of the reflection to analyze
    """
    with Session(database_engine) as session:
        # Get the reflection
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        if not reflection.answer:
            raise HTTPException(status_code=400, detail="Reflection must have an answer to be analyzed")
            
        # Analyze the reflection using LLM
        analysis = analyze_reflection(reflection)
        if not analysis:
            raise HTTPException(status_code=500, detail="Failed to analyze reflection")
        
        # Update reflection with analysis results
        reflection.sentiment = analysis.sentiment
        
        # Create theme entries and link them to the reflection
        for theme_name in analysis.themes:
            # Check if theme exists, if not create it
            theme = session.exec(select(Theme).where(Theme.name == theme_name)).first()
            if not theme:
                theme = Theme(name=theme_name)
                session.add(theme)
                session.commit()
                session.refresh(theme)
            
            # Link theme to reflection
            reflection_theme = ReflectionTheme(theme_id=theme.id, reflection_id=reflection.id)
            session.add(reflection_theme)
        
        # Create child reflections for each belief
        for belief in analysis.beliefs:
            child_reflection = Reflection(
                user_id=reflection.user_id,
                parent_id=reflection.id,
                language=reflection.language,
                type=ReflectionType(belief.belief_type),
                question=belief.challenge_question,
                context=belief.statement
            )
            session.add(child_reflection)
        
        session.commit()
        return {"message": "Reflection analyzed successfully"}

@app.get("/reflections/random/unanswered/{user_id}")
def get_random_unanswered_reflection(user_id: str):
    """
    Retrieve a random reflection that has no answer for the specified user.
    
    Args:
        user_id (str): The ID of the user requesting the reflection
    """
    with Session(database_engine) as session:
        # Query for reflections that have no answer and belong to the specified user
        unanswered_reflections = session.exec(
            select(Reflection)
            .where(Reflection.user_id == user_id)
            .where(Reflection.answer == None)  # Using None to check for NULL in database
            .limit(100)  # Limit the number of possible reflections to 100
        ).all()
        
        if not unanswered_reflections:
            raise HTTPException(
                status_code=404, 
                detail="No unanswered reflections found for this user"
            )
        
        # Return a random reflection from the list
        return random.choice(unanswered_reflections)

@app.delete("/reflections/{reflection_id}")
def delete_reflection(reflection_id: str):
    """
    Delete a reflection by ID. If the reflection has children, they will be
    reassigned to the parent of the deleted reflection.
    """
    with Session(database_engine) as session:
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        # Get all child reflections
        child_reflections = session.exec(
            select(Reflection).where(Reflection.parent_id == reflection_id)
        ).all()
        
        # Reassign children to the parent of the reflection being deleted
        for child in child_reflections:
            child.parent_id = reflection.parent_id
        
        # Delete the reflection
        session.delete(reflection)
        session.commit()
        return {"message": "Reflection deleted successfully"}

@app.post("/users/")
def create_user(user: User):
    """
    Create a new user and initialize with default reflection entries from the data files.
    """
    with Session(database_engine) as session:
        # Create user
        session.add(user)
        session.commit()
        session.refresh(user)
        
        # Load questions from the appropriate language file
        language_file = f"./data/{str(user.prefered_language)}.jsonl"
        try:
            with open(language_file, 'r', encoding='utf-8') as f:
                questions = [json.loads(line) for line in f]
                
            # Create initial reflections for the user
            for q in questions:
                reflection = Reflection(
                    user_id=user.id,
                    language=user.prefered_language,
                    type=ReflectionType(q['type']),
                    question=q['question']
                )
                session.add(reflection)
            
            session.commit()
            return user
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Error initializing user: {str(e)}")

@app.get("/users/{user_id}/stats")
def get_user_stats(user_id: str):
    """
    Get user statistics including total entries and number of answered entries.
    """
    with Session(database_engine) as session:
        # Verify user exists
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get total reflections count using COUNT
        total_count = session.exec(
            select(func.count())
            .select_from(Reflection)
            .where(Reflection.user_id == user_id)
        ).one()
        
        # Get answered reflections count using COUNT and WHERE
        answered_count = session.exec(
            select(func.count())
            .select_from(Reflection)
            .where(Reflection.user_id == user_id)
            .where(Reflection.answer != None)
        ).one()
        
        return {
            "total_entries": total_count,
            "answered_entries": answered_count
        }

@app.get("/users/{user_id}/reflections")
def get_user_reflections(user_id: str, offset: int = 0, limit: int = 100):
    """
    Get all reflections for a user with pagination.
    
    Args:
        user_id (str): The ID of the user
        offset (int): Number of records to skip (default: 0)
        limit (int): Maximum number of records to return (default: 100, max: 100)
    """
    if limit > 100:
        limit = 100
        
    with Session(database_engine) as session:
        # Verify user exists
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get paginated reflections
        reflections = session.exec(
            select(Reflection)
            .where(Reflection.user_id == user_id)
            .offset(offset)
            .limit(limit)
        ).all()
        
        return reflections

@app.get("/users/{user_id}/themes")
def get_user_themes(user_id: str, offset: int = 0, limit: int = 100):
    """
    Get all themes associated with a user's reflections with pagination.
    
    Args:
        user_id (str): The ID of the user
        offset (int): Number of records to skip (default: 0)
        limit (int): Maximum number of records to return (default: 100, max: 100)
    """
    if limit > 100:
        limit = 100
        
    with Session(database_engine) as session:
        # Verify user exists
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Start from Reflection (smaller table) and join to Theme
        stmt = (
            select(Theme)
            .distinct()
            .select_from(Reflection)
            .where(Reflection.user_id == user_id)
            .join(ReflectionTheme)
            .join(Theme)
            .offset(offset)
            .limit(limit)
        )
        
        themes = session.exec(stmt).all()
        return themes

@app.delete("/users/{user_id}")
def delete_user(user_id: str):
    """
    Delete a user and all associated reflections and theme relations.
    """
    with Session(database_engine) as session:
        # Verify user exists
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get all reflection IDs for this user
        user_reflections = session.exec(
            select(Reflection)
            .where(Reflection.user_id == user_id)
        ).all()
        
        # Delete all theme relations for these reflections
        for reflection in user_reflections:
            theme_relations = session.exec(
                select(ReflectionTheme)
                .where(ReflectionTheme.reflection_id == reflection.id)
            ).all()
            for relation in theme_relations:
                session.delete(relation)
        
        # Delete all reflections
        for reflection in user_reflections:
            session.delete(reflection)

        # Delete the user
        session.delete(user)
        session.commit()
        
        return {"message": "User and associated data deleted successfully"}

@app.get("/health")
def health_check():
    """
    Health endpoint to check database connection.
    """
    try:
        with Session(database_engine) as session:
            session.exec(select(1))
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database connection failed")

@app.get("/")
def root():
    return {"message": f"Welcome to {app.title} v{app.version}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
