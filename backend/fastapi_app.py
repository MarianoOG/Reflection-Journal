# Standard library imports
from contextlib import asynccontextmanager
import asyncio

# Third-party imports
from fastapi import FastAPI
from sqlmodel import create_engine
import uvicorn

# Local application imports
from config import Settings, logger
from models import create_db_and_tables
from routers import themes, reflections, auth, users, health
from ai_worker import ping_ai_worker

settings = Settings()
database_engine = None


async def keep_ai_worker_warm():
    """
    Background task that pings the AI Worker service every 5 minutes
    to prevent cold starts and keep the service responsive.
    """
    logger.info("Starting AI Worker keep-warm background task")
    while True:
        try:
            logger.info("Pinging AI Worker service to keep it warm...")
            success = ping_ai_worker()
            if success:
                logger.info("AI Worker service ping successful")
            else:
                logger.warning("AI Worker service ping failed")
            await asyncio.sleep(300)  # 5 minutes
        except asyncio.CancelledError:
            logger.info("Keep-warm task cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in keep-warm task: {e}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Manage application lifespan events.
    Starts database and background tasks on startup, cleanly shuts them down on exit.
    """
    # Startup
    global database_engine
    database_engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    create_db_and_tables(database_engine)
    logger.info("Application started with connection to the database")

    # Create and start the keep-warm background task
    keep_warm_task = asyncio.create_task(keep_ai_worker_warm())
    logger.info("Application started with AI Worker keep-warm task")

    yield

    # Shutdown
    logger.info("Shutting down, cancelling keep-warm task")
    keep_warm_task.cancel()
    try:
        await keep_warm_task
    except asyncio.CancelledError:
        pass


    logger.info("Shutting down, closing connection to database")
    database_engine.dispose()

app = FastAPI(lifespan=lifespan)
app.title = "Reflexion Journal - Backend"
app.version = "0.0.2"

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
