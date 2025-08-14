from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

router = APIRouter(tags=["Health"])

def get_database_engine():
    """Get the database engine from the main app context"""
    from fastapi_app import database_engine
    return database_engine

@router.get("/health", 
         summary="Health check", 
         description="Checks the database connection and returns the application's health status.")
def health_check():
    """
    Health endpoint to check database connection.
    """
    try:
        with Session(get_database_engine()) as session:
            session.exec(select(1))
        return {"status": "healthy"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database connection failed")