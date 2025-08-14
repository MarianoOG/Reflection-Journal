# Standard library imports
from contextlib import asynccontextmanager

# Third-party imports
from fastapi import FastAPI
from sqlmodel import create_engine
import uvicorn

# Local application imports
from config import Settings
from models import create_db_and_tables
from routers import themes, reflections, auth, users, health

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

# Include routers
app.include_router(themes.router)
app.include_router(reflections.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(health.router)


@app.get("/", 
         tags=["Root"], 
         summary="Welcome Endpoint",
         description="Returns a welcome message including the application title and version.")
def root():
    return {"message": f"Welcome to {app.title} v{app.version}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
