from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from models import User, Reflection, ReflectionTheme, UserResponse
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

@router.get("/me/stats", 
         summary="Get user statistics", 
         description="Retrieves statistics for the authenticated user including total and answered reflection counts.")
def get_user_stats(current_user: User = Depends(get_current_user_dep)):
    """
    Get user statistics including total entries and number of answered entries.
    """
    with Session(get_database_engine()) as session:
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