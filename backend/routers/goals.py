from fastapi import APIRouter, HTTPException, Body, Path, Depends
from sqlmodel import Session, select, func
from datetime import datetime

from models import User, Goal
from config import get_current_user_dep

router = APIRouter(prefix="/goals", tags=["Goals"])

def get_database_engine():
    """Get the database engine from the main app context"""
    from fastapi_app import database_engine
    return database_engine


@router.get("/",
         summary="List goals",
         description="Retrieves all goals owned by the authenticated user (max 5).")
def list_goals(current_user: User = Depends(get_current_user_dep)):
    """
    List all goals owned by the authenticated user.
    Maximum of 5 goals per user.
    """
    with Session(get_database_engine()) as session:
        goals = session.exec(
            select(Goal)
            .where(Goal.user_id == current_user.id)
            .limit(5)
        ).all()
        return goals


@router.put("/",
         summary="Upsert a goal",
         description="Creates or updates a goal for the authenticated user. Maximum 5 goals per user.")
def upsert_goal(goal: Goal = Body(..., description="Goal object to upsert"),
                current_user: User = Depends(get_current_user_dep)):
    """
    Upsert a goal. If goal.id exists, update it; if not, create new.
    Only allows operations on goals owned by the authenticated user.
    Maximum of 5 goals per user.
    """
    with Session(get_database_engine()) as session:
        existing_goal = session.get(Goal, goal.id)

        if existing_goal:
            # Update existing goal
            # Verify ownership
            if existing_goal.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to modify this goal")

            existing_goal.title = goal.title
            existing_goal.description = goal.description
            existing_goal.goal_type = goal.goal_type
            existing_goal.target_value = goal.target_value
            existing_goal.current_value = goal.current_value
            existing_goal.unit = goal.unit
            existing_goal.current_confidence = goal.current_confidence
            existing_goal.justification = goal.justification
            existing_goal.deadline = goal.deadline
            existing_goal.priority = goal.priority
            existing_goal.status = goal.status
            existing_goal.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(existing_goal)
            return existing_goal
        else:
            # Create new goal - check limit
            goal_count = session.exec(
                select(func.count(Goal.id)).where(Goal.user_id == current_user.id)
            ).one()

            if goal_count >= 5:
                raise HTTPException(status_code=400, detail="Maximum of 5 goals per user reached")

            # Ensure the goal belongs to the authenticated user
            goal.user_id = current_user.id
            # Set initial_confidence from current_confidence if provided
            if goal.current_confidence and not goal.initial_confidence:
                goal.initial_confidence = goal.current_confidence
            session.add(goal)
            session.commit()
            session.refresh(goal)
            return goal


@router.delete("/{goal_id}",
            summary="Delete goal",
            description="Deletes a goal owned by the authenticated user.")
def delete_goal(goal_id: str = Path(..., description="Unique identifier of the goal to delete"),
                current_user: User = Depends(get_current_user_dep)):
    """
    Delete a goal by ID owned by the authenticated user.
    """
    with Session(get_database_engine()) as session:
        goal = session.get(Goal, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        # Verify ownership
        if goal.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this goal")

        # Delete the goal
        session.delete(goal)
        session.commit()
        return {"message": "Goal deleted successfully"}
