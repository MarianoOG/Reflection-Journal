from fastapi import APIRouter, HTTPException, Body, Path, Query, Depends
from sqlmodel import Session, select

from models import User, Theme, Reflection, ReflectionTheme
from config import get_current_user_dep

router = APIRouter(prefix="/reflections", tags=["Reflections"])

def get_database_engine():
    """Get the database engine from the main app context"""
    from fastapi_app import database_engine
    return database_engine

@router.get("/", 
         summary="List reflections", 
         description="Retrieves reflections owned by the authenticated user with pagination.")
def list_reflections(offset: int = Query(0, description="Number of records to skip."), 
                limit: int = Query(100, description="Maximum number of records to return, capped at 100.", le=100, gt=0),
                current_user: User = Depends(get_current_user_dep)):
    """
    List reflections owned by the authenticated user with pagination.
    
    Args:
        offset (int): Number of records to skip (default: 0)
        limit (int): Maximum number of records to return (default: 100, max: 100)
    """
    
    with Session(get_database_engine()) as session:
        reflections = session.exec(
            select(Reflection)
            .where(Reflection.user_id == current_user.id)
            .order_by(Reflection.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return reflections

@router.put("/", 
         summary="Upsert a reflection", 
         description="Creates or updates a reflection for the authenticated user. If a reflection with the provided ID exists, it is updated; otherwise, a new reflection is created.")
def upsert_reflection(reflection: Reflection = Body(..., description="Reflection object to upsert"), current_user: User = Depends(get_current_user_dep)):
    """
    Upsert a reflection. If reflection_id exists, update it; if not, create new with specified ID.
    Only allows operations on reflections owned by the authenticated user.
    """
    with Session(get_database_engine()) as session:
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

@router.get("/{reflection_id}", 
         summary="Get a reflection", 
         description="Retrieves a reflection by its unique identifier for the authenticated user.")
def get_reflection(reflection_id: str = Path(..., description="Unique identifier of the reflection"), current_user: User = Depends(get_current_user_dep)):
    """
    Retrieve a reflection by ID for the authenticated user.
    """
    with Session(get_database_engine()) as session:
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        # Verify ownership
        if reflection.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this reflection")
        
        return reflection

@router.get("/{reflection_id}/parent", 
         summary="Get reflection parent", 
         description="Retrieves the parent reflection of the given reflection for the authenticated user.")
def get_reflection_parent(reflection_id: str = Path(..., description="Identifier of the reflection whose parent is to be retrieved"), current_user: User = Depends(get_current_user_dep)):
    """
    Retrieve the parent reflection of a given reflection ID for the authenticated user.
    """
    with Session(get_database_engine()) as session:
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        # Verify ownership
        if reflection.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this reflection")
        
        if not reflection.parent_id:
            return None
            
        parent = session.get(Reflection, reflection.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent reflection not found")
        
        # Verify parent ownership as well
        if parent.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access parent reflection")
        
        return parent

@router.get("/{reflection_id}/children", 
         summary="Get reflection children", 
         description="Retrieves all child reflections for the given reflection for the authenticated user.")
def get_reflection_children(reflection_id: str = Path(..., description="Identifier of the reflection whose children are requested"), current_user: User = Depends(get_current_user_dep)):
    """
    Retrieve all child reflections of a given reflection ID for the authenticated user.
    """
    with Session(get_database_engine()) as session:
        # First verify the parent reflection exists and is owned by user
        parent = session.get(Reflection, reflection_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        # Verify ownership
        if parent.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this reflection")
            
        children = session.exec(
            select(Reflection).where(Reflection.parent_id == reflection_id).where(Reflection.user_id == current_user.id)
        ).all()
        return children

@router.get("/{reflection_id}/themes", 
         summary="Get reflection themes", 
         description="Retrieves all themes associated with the given reflection for the authenticated user.")
def get_reflection_themes(reflection_id: str = Path(..., description="Unique identifier of the reflection to get themes for"), current_user: User = Depends(get_current_user_dep)):
    """
    Retrieve all themes associated with a given reflection ID for the authenticated user.
    
    Args:
        reflection_id (str): The ID of the reflection
    """
    with Session(get_database_engine()) as session:
        # Verify reflection exists and is owned by user
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        # Verify ownership
        if reflection.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this reflection")
        
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

@router.post("/{reflection_id}/themes/{theme_id}", 
            summary="Connect theme to reflection", 
            description="Creates a connection between a reflection and a theme, both owned by the authenticated user.")
def connect_theme_to_reflection(reflection_id: str = Path(..., description="Unique identifier of the reflection"), 
                               theme_id: str = Path(..., description="Unique identifier of the theme"),
                               current_user: User = Depends(get_current_user_dep)):
    """
    Connect a theme to a reflection. Both must be owned by the authenticated user.
    """
    with Session(get_database_engine()) as session:
        # Verify reflection exists and is owned by user
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        if reflection.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this reflection")
        
        # Verify theme exists and is owned by user
        theme = session.get(Theme, theme_id)
        if not theme:
            raise HTTPException(status_code=404, detail="Theme not found")
        
        if theme.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this theme")
        
        # Check if connection already exists
        existing_connection = session.exec(
            select(ReflectionTheme)
            .where(ReflectionTheme.reflection_id == reflection_id)
            .where(ReflectionTheme.theme_id == theme_id)
        ).first()
        
        if existing_connection:
            raise HTTPException(status_code=409, detail="Theme is already connected to this reflection")
        
        # Create the connection
        reflection_theme = ReflectionTheme(
            reflection_id=reflection_id,
            theme_id=theme_id
        )
        session.add(reflection_theme)
        session.commit()
        session.refresh(reflection_theme)
        
        return {"message": "Theme connected to reflection successfully", "connection_id": reflection_theme.id}

@router.delete("/{reflection_id}/themes/{theme_id}", 
              summary="Disconnect theme from reflection", 
              description="Removes the connection between a reflection and a theme, both owned by the authenticated user.")
def disconnect_theme_from_reflection(reflection_id: str = Path(..., description="Unique identifier of the reflection"), 
                                   theme_id: str = Path(..., description="Unique identifier of the theme"),
                                   current_user: User = Depends(get_current_user_dep)):
    """
    Disconnect a theme from a reflection. Both must be owned by the authenticated user.
    """
    with Session(get_database_engine()) as session:
        # Verify reflection exists and is owned by user
        reflection = session.get(Reflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        if reflection.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this reflection")
        
        # Verify theme exists and is owned by user
        theme = session.get(Theme, theme_id)
        if not theme:
            raise HTTPException(status_code=404, detail="Theme not found")
        
        if theme.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this theme")
        
        # Find the connection
        connection = session.exec(
            select(ReflectionTheme)
            .where(ReflectionTheme.reflection_id == reflection_id)
            .where(ReflectionTheme.theme_id == theme_id)
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection between theme and reflection not found")
        
        # Delete the connection
        session.delete(connection)
        session.commit()
        
        return {"message": "Theme disconnected from reflection successfully"}

@router.delete("/{reflection_id}", 
            summary="Delete reflection", 
            description="Deletes a reflection owned by the authenticated user and reassigns its children to its parent if applicable.")
def delete_reflection(reflection_id: str = Path(..., description="Unique identifier of the reflection to delete"), current_user: User = Depends(get_current_user_dep)):
    """
    Delete a reflection by ID owned by the authenticated user. If the reflection has children, they will be
    reassigned to the parent of the deleted reflection.
    """
    with Session(get_database_engine()) as session:
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