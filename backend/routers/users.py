from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import List

from models import User, Reflection, ReflectionTheme, UserResponse, Theme, UserUpdate, UserStats, UserSentimentData, SentimentByDate, SentimentType
from config import get_current_user_dep

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


@router.get("/me/stats",
         summary="Get user reflection statistics",
         description="Get total entries, entries with answers, and follow-up questions without answers.",
         response_model=UserStats)
def get_user_stats(current_user: User = Depends(get_current_user_dep)):
    """
    Get statistics about the currently authenticated user's reflections:
    - Total number of entries
    - Number of entries with answers
    - Number of follow-up questions without answers
    """
    with Session(get_database_engine()) as session:
        # Get all reflections for the user
        all_reflections = session.exec(
            select(Reflection)
            .where(Reflection.user_id == current_user.id)
        ).all()

        total_entries = len(all_reflections)
        entries_with_answers = len([r for r in all_reflections if r.answer is not None])
        follow_up_questions_without_answers = len([r for r in all_reflections if r.answer is None])

        return UserStats(
            total_entries=total_entries,
            entries_with_answers=entries_with_answers,
            follow_up_questions_without_answers=follow_up_questions_without_answers
        )


@router.get("/me/sentiment_by_date",
         summary="Get sentiment data by date",
         description="Get average sentiment per day for the last 30 days with entries.",
         response_model=UserSentimentData)
def get_user_sentiment_by_date(current_user: User = Depends(get_current_user_dep)):
    """
    Get sentiment trend data for the currently authenticated user.
    Returns average sentiment per day for the last 30 days (only days with entries).

    Sentiment values:
    - Positive: 1
    - Neutral: 0
    - Negative: -1
    """
    with Session(get_database_engine()) as session:
        # Get all reflections for the user from the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        reflections = session.exec(
            select(Reflection)
            .where(Reflection.user_id == current_user.id)
            .where(Reflection.created_at >= thirty_days_ago)
            .where(Reflection.answer.isnot(None))  # type:ignore
        ).all()

        # Group by date and calculate average sentiment
        sentiment_by_date_dict = {}

        for reflection in reflections:
            # Extract date only (YYYY-MM-DD)
            date_key = reflection.created_at.date().isoformat()

            # Convert sentiment enum to numeric value
            if reflection.sentiment == SentimentType.POSITIVE:
                sentiment_value = 1
            elif reflection.sentiment == SentimentType.NEUTRAL:
                sentiment_value = 0
            else:  # NEGATIVE
                sentiment_value = -1

            # Add to dict for averaging
            if date_key not in sentiment_by_date_dict:
                sentiment_by_date_dict[date_key] = []
            sentiment_by_date_dict[date_key].append(sentiment_value)

        # Calculate averages and create result
        sentiment_data = []
        for date_key in sorted(sentiment_by_date_dict.keys()):
            sentiments = sentiment_by_date_dict[date_key]
            avg_sentiment = sum(sentiments) / len(sentiments)
            sentiment_data.append(SentimentByDate(
                date=date_key,
                sentiment_value=avg_sentiment,
                entries_count=len(sentiments)
            ))

        return UserSentimentData(sentiment_data=sentiment_data)


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
