# Standard library imports
import random
from datetime import datetime
from contextlib import asynccontextmanager
import json

# Third-party imports
from fastapi import FastAPI, HTTPException, Query, Body, Path
from sqlmodel import Session, create_engine, select, func
import uvicorn

# Local application imports
from config import Settings
from llm import analyze_reflection
from models import User, Theme, Reflection, ReflectionTheme, ReflectionType, create_db_and_tables

settings = Settings()
database_engine = None

@asynccontextmanager
async def lifespan(_: FastAPI):
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


@app.get("/themes", 
         tags=["Themes"], 
         summary="List themes", 
         description="Retrieves themes with pagination. Adjust offset and limit to page through results.")
def list_themes(offset: int = Query(0, description="Number of records to skip."), 
                limit: int = Query(100, description="Maximum number of records to return, capped at 100.")):
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

@app.get("/themes/{theme_id}/reflections", 
         tags=["Themes"], 
         summary="Get reflections for a theme", 
         description="Returns all reflections associated with the given theme.")
def get_theme_reflections(theme_id: str = Path(..., description="ID of the theme whose reflections are retrieved")):
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

@app.delete("/themes/{theme_id}", 
            tags=["Themes"], 
            summary="Delete theme", 
            description="Deletes the specified theme and all its reflection relations.")
def delete_theme(theme_id: str = Path(..., description="ID of the theme to delete")):
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

@app.get("/reflections", 
         tags=["Reflections"], 
         summary="List reflections", 
         description="Retrieves reflections with pagination.")
def list_reflections(offset: int = Query(0, description="Number of records to skip."), 
                     limit: int = Query(100, description="Maximum number of records to return, capped at 100.")):
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

@app.put("/reflections/", 
         tags=["Reflections"], 
         summary="Upsert a reflection", 
         description="Creates or updates a reflection. If a reflection with the provided ID exists, it is updated; otherwise, a new reflection is created.")
def upsert_reflection(reflection: Reflection = Body(..., description="Reflection object to upsert")):
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

@app.get("/reflections/{reflection_id}", 
         tags=["Reflections"], 
         summary="Get a reflection", 
         description="Retrieves a reflection by its unique identifier.")
def get_reflection(reflection_id: str = Path(..., description="Unique identifier of the reflection")):
    """
    Retrieve a reflection by ID.
    """
    with Session(database_engine) as session:
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        return reflection

@app.get("/reflections/{reflection_id}/parent", 
         tags=["Reflections"], 
         summary="Get reflection parent", 
         description="Retrieves the parent reflection of the given reflection.")
def get_reflection_parent(reflection_id: str = Path(..., description="Identifier of the reflection whose parent is to be retrieved")):
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

@app.get("/reflections/{reflection_id}/children", 
         tags=["Reflections"], 
         summary="Get reflection children", 
         description="Retrieves all child reflections for the given reflection.")
def get_reflection_children(reflection_id: str = Path(..., description="Identifier of the reflection whose children are requested")):
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

@app.get("/reflections/{reflection_id}/themes", 
         tags=["Reflections"], 
         summary="Get reflection themes", 
         description="Retrieves all themes associated with the given reflection.")
def get_reflection_themes(reflection_id: str = Path(..., description="Unique identifier of the reflection to get themes for")):
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

@app.post("/reflections/{reflection_id}/analyze", 
          tags=["Reflections"], 
          summary="Analyze reflection", 
          description="Analyzes the reflection using LLM and updates its sentiment, themes and creates child reflections based on beliefs.")
def analyze_reflection_by_id(reflection_id: str = Path(..., description="Unique identifier of the reflection to analyze")):
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

@app.get("/reflections/random/unanswered/{user_id}", 
         tags=["Reflections"], 
         summary="Get random unanswered reflection", 
         description="Retrieves a random reflection without an answer for the specified user.")
def get_random_unanswered_reflection(user_id: str = Path(..., description="User identifier for which an unanswered reflection is requested")):
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

@app.delete("/reflections/{reflection_id}", 
            tags=["Reflections"], 
            summary="Delete reflection", 
            description="Deletes a reflection and reassigns its children to its parent if applicable.")
def delete_reflection(reflection_id: str = Path(..., description="Unique identifier of the reflection to delete")):
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

@app.post("/users/", 
          tags=["Users"], 
          summary="Create user", 
          description="Creates a new user and initializes default reflection entries from language-specific question files.")
def create_user(user: User = Body(..., description="User data for creating a new user")):
    """
    Create a new user and initialize with default reflection entries from the data files.
    If a user with the given ID already exists, returns 409 Conflict.
    """
    with Session(database_engine) as session:
        # Check if user already exists
        existing_user = session.get(User, user.id)
        if existing_user:
            raise HTTPException(status_code=409, detail="User with this ID already exists")
        
        # Load questions from the appropriate language file
        language_file = f"./questions/{str(user.prefered_language)}.jsonl"

        try:
            # Create user
            session.add(user)
            session.commit()

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
            session.refresh(user)
            return user
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Error initializing user: {str(e)}")

@app.get("/users/{email}", 
         tags=["Users"], 
         summary="Get user by email", 
         description="Retrieves a user by email and updates their last login timestamp.")
def get_user_by_email(email: str = Path(..., description="Email address of the user")):
    """
    Get a user by email.
    """
    with Session(database_engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.last_login = datetime.now()
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

@app.get("/users/{user_id}/stats", 
         tags=["Users"], 
         summary="Get user statistics", 
         description="Retrieves statistics for the user including total and answered reflection counts.")
def get_user_stats(user_id: str = Path(..., description="Unique identifier of the user")):
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

@app.get("/users/{user_id}/reflections", 
         tags=["Users"], 
         summary="Get user reflections", 
         description="Retrieves reflections for the specified user with pagination.")
def get_user_reflections(user_id: str = Path(..., description="User identifier"), 
                         offset: int = Query(0, description="Number of records to skip"), 
                         limit: int = Query(100, description="Maximum number of reflections to return, capped at 100")):
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

@app.get("/users/{user_id}/themes", 
         tags=["Users"], 
         summary="Get user themes", 
         description="Retrieves themes associated with the user's reflections with pagination.")
def get_user_themes(user_id: str = Path(..., description="User identifier"), 
                    offset: int = Query(0, description="Number of records to skip"), 
                    limit: int = Query(100, description="Maximum number of themes to return, capped at 100")):
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

@app.delete("/users/{user_id}", 
            tags=["Users"], 
            summary="Delete user", 
            description="Deletes a user and all associated reflections and theme relations.")
def delete_user(user_id: str = Path(..., description="Unique identifier of the user to delete")):
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

@app.get("/health", 
         tags=["Health"], 
         summary="Health check", 
         description="Checks the database connection and returns the application's health status.")
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

@app.get("/", 
         tags=["Root"], 
         summary="Welcome Endpoint",
         description="Returns a welcome message including the application title and version.")
def root():
    return {"message": f"Welcome to {app.title} v{app.version}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
