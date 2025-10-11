from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends
from sqlmodel import Session, select

from models import User, Theme, Reflection, ReflectionTheme
from config import get_current_user_dep

router = APIRouter(prefix="/themes", tags=["Themes"])

def get_database_engine():
    """Get the database engine from the main app context"""
    from fastapi_app import database_engine
    return database_engine

@router.get("/", 
         summary="List themes", 
         description="Retrieves themes owned by the authenticated user with pagination.")
def list_themes(offset: int = Query(0, description="Number of records to skip."), 
                limit: int = Query(100, description="Maximum number of records to return, capped at 100."),
                current_user: User = Depends(get_current_user_dep)):
    """
    List themes owned by the authenticated user with pagination.
    
    Args:
        offset (int): Number of records to skip (default: 0)
        limit (int): Maximum number of records to return (default: 100, max: 100)
    """
    if limit > 100:
        limit = 100
    
    with Session(get_database_engine()) as session:
        themes = session.exec(
            select(Theme)
            .where(Theme.user_id == current_user.id)
            .offset(offset)
            .limit(limit)
        ).all()
        return themes

@router.put("/", 
         summary="Upsert a theme", 
         description="Creates or updates a theme for the authenticated user. If a theme with the provided ID exists, it is updated; otherwise, a new theme is created.")
def upsert_theme(theme: Theme = Body(..., description="Theme object to upsert"), current_user: User = Depends(get_current_user_dep)):
    """
    Upsert a theme. If theme_id exists, update it; if not, create new with specified ID.
    Only allows operations on themes owned by the authenticated user.
    """
    with Session(get_database_engine()) as session:
        existing_theme = session.get(Theme, theme.id)
        if existing_theme:
            # Verify ownership
            if existing_theme.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to modify this theme")
            
            existing_theme.name = theme.name
        else:
            # Ensure the theme belongs to the authenticated user
            theme.user_id = current_user.id
            session.add(theme)
        session.commit()
        session.refresh(existing_theme if existing_theme else theme)
        return existing_theme if existing_theme else theme

@router.get("/{theme_id}/reflections", 
         summary="Get reflections for a theme", 
         description="Returns all reflections associated with the given theme owned by the authenticated user.")
def get_theme_reflections(theme_id: str = Path(..., description="ID of the theme whose reflections are retrieved"),
                         current_user: User = Depends(get_current_user_dep)):
    """
    Retrieve all reflections associated with a given theme ID owned by the authenticated user.
    
    Args:
        theme_id (str): The ID of the theme
    """
    with Session(get_database_engine()) as session:
        # Verify theme exists and is owned by user
        theme = session.get(Theme, theme_id)
        if not theme:
            raise HTTPException(status_code=404, detail="Theme not found")
        
        # Verify ownership
        if theme.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this theme")
        
        # Get all reflection relations for this theme
        reflection_relations = session.exec(
            select(ReflectionTheme).where(ReflectionTheme.theme_id == theme_id)
        ).all()
        
        # Get all reflections owned by the user
        reflections = dict()
        for relation in reflection_relations:
            reflection = session.get(Reflection, relation.reflection_id)
            if reflection and reflection.user_id == current_user.id:
                reflections[reflection.id] = reflection
        
        return list(reflections.values())

@router.delete("/{theme_id}", 
            summary="Delete theme", 
            description="Deletes the specified theme owned by the authenticated user and all its reflection relations.")
def delete_theme(theme_id: str = Path(..., description="ID of the theme to delete"), 
                 current_user: User = Depends(get_current_user_dep)):
    """
    Delete a theme by ID owned by the authenticated user and all its relations in ReflectionTheme.
    """
    with Session(get_database_engine()) as session:
        theme = session.get(Theme, theme_id)
        if not theme:
            raise HTTPException(status_code=404, detail="Theme not found")
        
        # Verify ownership
        if theme.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this theme")
        
        # Delete all ReflectionTheme relations for this theme
        reflection_themes = session.exec(select(ReflectionTheme).where(ReflectionTheme.theme_id == theme_id)).all()
        for relation in reflection_themes:
            session.delete(relation)
        
        # Delete the theme itself
        session.delete(theme)
        session.commit()
        return {"message": "Theme and its relations deleted successfully"}
    