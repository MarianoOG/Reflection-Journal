import logging
from sqlmodel import SQLModel, create_engine, Session, select
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import uvicorn
from config import Settings
from models import User, Theme, Reflection, ReflectionTheme, ReflectionHierarchy, Languages

settings = Settings()
database_engine = None

def create_db_and_tables(engine):
    logging.info("Creating database and tables...")
    try:
        SQLModel.metadata.create_all(engine)
        logging.info("Database and tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database and tables: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    global database_engine
    database_engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False}, echo=True)
    create_db_and_tables(database_engine)
    yield
    # Shutdown
    database_engine.dispose()

app = FastAPI(lifespan=lifespan)
app.title = "Reflexion Journal"
app.version = "0.0.1"

@app.get("/health")
def health_check():
    """
    Health endpoint to check database connection.
    """
    try:
        with Session(database_engine) as session:
            session.exec(select(User))
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database connection failed")

@app.get("/")
def root():
    return {"message": f"Welcome to {app.title} v{app.version}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
