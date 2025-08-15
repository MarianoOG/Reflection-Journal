from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from models import User, Reflection, ReflectionTheme, UserResponse, Theme, UserUpdate
from auth import get_current_user_dep

router = APIRouter(prefix="/users", tags=["Users"])

def get_database_engine():
    """Get the database engine from the main app context"""
    from fastapi_app import database_engine
    return database_engine


@router.get("/me", 
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


@router.put("/me", 
         summary="Update current user", 
         description="Update information about the currently authenticated user.",
         response_model=UserResponse)
def update_current_user_info(user_update: UserUpdate, current_user: User = Depends(get_current_user_dep)):
    """
    Update information about the currently authenticated user.
    """
    with Session(get_database_engine()) as session:
        # Get fresh user instance from session
        user_to_update = session.get(User, current_user.id)
        if not user_to_update:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields if provided
        if user_update.name is not None:
            user_to_update.name = user_update.name
        if user_update.prefered_language is not None:
            user_to_update.prefered_language = user_update.prefered_language
        
        session.add(user_to_update)
        session.commit()
        session.refresh(user_to_update)
        
        return UserResponse(
            id=user_to_update.id,
            name=user_to_update.name,
            email=user_to_update.email,
            prefered_language=user_to_update.prefered_language,
            last_login=user_to_update.last_login,
            created_at=user_to_update.created_at
        )


@router.delete("/me", 
            summary="Delete current user", 
            description="Deletes the authenticated user and all associated reflections and theme relations.")
def delete_user(current_user: User = Depends(get_current_user_dep)):
    """
    Delete the authenticated user and all associated reflections and theme relations.
    """
    with Session(get_database_engine()) as session:
        # Get all reflection IDs for the authenticated user
        user_reflections = session.exec(
            select(Reflection)
            .where(Reflection.user_id == current_user.id)
        ).all()

        # Get all theme IDs for the authenticated user
        user_themes = session.exec(
            select(Theme)
            .where(Theme.user_id == current_user.id)
        ).all()
        
        # Delete all theme relations for these reflections
        for reflection in user_reflections:
            theme_relations = session.exec(
                select(ReflectionTheme)
                .where(ReflectionTheme.reflection_id == reflection.id)
            ).all()
            for relation in theme_relations:
                session.delete(relation)

        # Delete all theme relations for these themes
        for theme in user_themes:
            theme_relations = session.exec(
                select(ReflectionTheme)
                .where(ReflectionTheme.theme_id == theme.id)
            ).all()
            for relation in theme_relations:
                session.delete(relation)

        # Delete all themes
        for theme in user_themes:
            session.delete(theme)
        
        # Delete all reflections
        for reflection in user_reflections:
            session.delete(reflection)

        # Delete the user (need to get fresh instance from session)
        user_to_delete = session.get(User, current_user.id)
        session.delete(user_to_delete)
        session.commit()
        
        return {"message": "User and associated data deleted successfully"}
