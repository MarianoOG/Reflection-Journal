# Standard library imports
import random
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import json

# Third-party imports
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Body, Path, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, create_engine, select, func
import uvicorn

# Local application imports
from config import Settings
from llm import analyze_reflection
from models import User, Theme, Reflection, ReflectionTheme, ReflectionType, create_db_and_tables, UserCreate, UserLogin, Token, UserResponse
from auth import authenticate_user, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES

settings = Settings()
database_engine = None

# Create security instance that returns 401 instead of 403
security = HTTPBearer(auto_error=False)

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

# Create auth dependency with database session
def get_current_user_dep(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    with Session(database_engine) as session:
        from auth import verify_token
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        # Check if credentials are provided
        if credentials is None:
            raise credentials_exception
        
        user = verify_token(credentials.credentials, session)
        if user is None:
            raise credentials_exception
        return user


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
         description="Creates or updates a reflection for the authenticated user. If a reflection with the provided ID exists, it is updated; otherwise, a new reflection is created.")
def upsert_reflection(reflection: Reflection = Body(..., description="Reflection object to upsert"), current_user: User = Depends(get_current_user_dep)):
    """
    Upsert a reflection. If reflection_id exists, update it; if not, create new with specified ID.
    Only allows operations on reflections owned by the authenticated user.
    """
    with Session(database_engine) as session:
        existing_reflection = session.get(Reflection, reflection.id)
        if existing_reflection:
            # Verify ownership
            if existing_reflection.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to modify this reflection")
            
            existing_reflection.parent_id = reflection.parent_id
            existing_reflection.language = reflection.language
            existing_reflection.type = reflection.type
            existing_reflection.sentiment = reflection.sentiment
            existing_reflection.context = reflection.context
            existing_reflection.question = reflection.question
            existing_reflection.answer = reflection.answer
        else:
            # Ensure the reflection belongs to the authenticated user
            reflection.user_id = current_user.id
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

@app.get("/reflections/random/unanswered", 
         tags=["Reflections"], 
         summary="Get random unanswered reflection", 
         description="Retrieves a random reflection without an answer for the authenticated user.")
def get_random_unanswered_reflection(current_user: User = Depends(get_current_user_dep)):
    """
    Retrieve a random reflection that has no answer for the authenticated user.
    """
    with Session(database_engine) as session:
        # Query for reflections that have no answer and belong to the authenticated user
        unanswered_reflections = session.exec(
            select(Reflection)
            .where(Reflection.user_id == current_user.id)
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
            description="Deletes a reflection owned by the authenticated user and reassigns its children to its parent if applicable.")
def delete_reflection(reflection_id: str = Path(..., description="Unique identifier of the reflection to delete"), current_user: User = Depends(get_current_user_dep)):
    """
    Delete a reflection by ID owned by the authenticated user. If the reflection has children, they will be
    reassigned to the parent of the deleted reflection.
    """
    with Session(database_engine) as session:
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        # Verify ownership
        if reflection.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this reflection")
        
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

@app.post("/auth/register", 
          tags=["Authentication"], 
          summary="Register user", 
          description="Creates a new user account with password authentication.",
          response_model=UserResponse)
def register_user(user_data: UserCreate = Body(..., description="User registration data")):
    """
    Create a new user account with password authentication.
    """
    with Session(database_engine) as session:
        # Check if user already exists
        existing_user = session.exec(select(User).where(User.email == user_data.email)).first()
        if existing_user:
            raise HTTPException(status_code=409, detail="User with this email already exists")
        
        # Hash password and create user
        password_hash = get_password_hash(user_data.password)
        user = User(
            name=user_data.name,
            email=user_data.email,
            password_hash=password_hash
        )
        
        try:
            # Create user
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Return user response without password hash
            return UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                prefered_language=user.prefered_language,
                last_login=user.last_login,
                created_at=user.created_at
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.post("/auth/login", 
          tags=["Authentication"], 
          summary="Login user", 
          description="Authenticate user with email and password, returns JWT token.",
          response_model=Token)
def login_user(login_data: UserLogin = Body(..., description="User login credentials")):
    """
    Authenticate user and return JWT access token.
    """
    with Session(database_engine) as session:
        user = authenticate_user(login_data.email, login_data.password, session)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last login
        user.last_login = datetime.now()
        session.add(user)
        session.commit()
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")

@app.get("/auth/me", 
         tags=["Authentication"], 
         summary="Get current user", 
         description="Get information about the currently authenticated user.",
         response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user_dep)):
    """
    Get information about the currently authenticated user.
    """
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        prefered_language=current_user.prefered_language,
        last_login=current_user.last_login,
        created_at=current_user.created_at
    )


@app.get("/users/me/stats", 
         tags=["Users"], 
         summary="Get user statistics", 
         description="Retrieves statistics for the authenticated user including total and answered reflection counts.")
def get_user_stats(current_user: User = Depends(get_current_user_dep)):
    """
    Get user statistics including total entries and number of answered entries.
    """
    with Session(database_engine) as session:
        # Get total reflections count using COUNT
        total_count = session.exec(
            select(func.count())
            .select_from(Reflection)
            .where(Reflection.user_id == current_user.id)
        ).one()
        
        # Get answered reflections count using COUNT and WHERE
        answered_count = session.exec(
            select(func.count())
            .select_from(Reflection)
            .where(Reflection.user_id == current_user.id)
            .where(Reflection.answer != None)
        ).one()
        
        return {
            "total_entries": total_count,
            "answered_entries": answered_count
        }

@app.get("/users/me/reflections", 
         tags=["Users"], 
         summary="Get user reflections", 
         description="Retrieves reflections for the authenticated user with pagination.")
def get_user_reflections(current_user: User = Depends(get_current_user_dep),
                         offset: int = Query(0, description="Number of records to skip"), 
                         limit: int = Query(100, description="Maximum number of reflections to return, capped at 100")):
    """
    Get all reflections for the authenticated user with pagination.
    
    Args:
        offset (int): Number of records to skip (default: 0)
        limit (int): Maximum number of records to return (default: 100, max: 100)
    """
    if limit > 100:
        limit = 100
        
    with Session(database_engine) as session:
        # Get paginated reflections for the authenticated user
        reflections = session.exec(
            select(Reflection)
            .where(Reflection.user_id == current_user.id)
            .offset(offset)
            .limit(limit)
        ).all()
        
        return reflections

@app.get("/users/me/themes", 
         tags=["Users"], 
         summary="Get user themes", 
         description="Retrieves themes associated with the authenticated user's reflections with pagination.")
def get_user_themes(current_user: User = Depends(get_current_user_dep),
                    offset: int = Query(0, description="Number of records to skip"), 
                    limit: int = Query(100, description="Maximum number of themes to return, capped at 100")):
    """
    Get all themes associated with the authenticated user's reflections with pagination.
    
    Args:
        offset (int): Number of records to skip (default: 0)
        limit (int): Maximum number of records to return (default: 100, max: 100)
    """
    if limit > 100:
        limit = 100
        
    with Session(database_engine) as session:
        # Start from Reflection (smaller table) and join to Theme
        stmt = (
            select(Theme)
            .distinct()
            .select_from(Reflection)
            .where(Reflection.user_id == current_user.id)
            .join(ReflectionTheme)
            .join(Theme)
            .offset(offset)
            .limit(limit)
        )
        
        themes = session.exec(stmt).all()
        return themes

@app.delete("/users/me", 
            tags=["Users"], 
            summary="Delete current user", 
            description="Deletes the authenticated user and all associated reflections and theme relations.")
def delete_user(current_user: User = Depends(get_current_user_dep)):
    """
    Delete the authenticated user and all associated reflections and theme relations.
    """
    with Session(database_engine) as session:
        # Get all reflection IDs for the authenticated user
        user_reflections = session.exec(
            select(Reflection)
            .where(Reflection.user_id == current_user.id)
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

        # Delete the user (need to get fresh instance from session)
        user_to_delete = session.get(User, current_user.id)
        session.delete(user_to_delete)
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
    except Exception:
        raise HTTPException(status_code=503, detail="Database connection failed")

@app.get("/", 
         tags=["Root"], 
         summary="Welcome Endpoint",
         description="Returns a welcome message including the application title and version.")
def root():
    return {"message": f"Welcome to {app.title} v{app.version}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
