from fastapi import FastAPI, HTTPException, Body, Security
from fastapi.security import APIKeyHeader
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from models import QnAPair, LLMEntryAnalysis
from llm_inference import analyze_reflection, ping_llm
from config import logger, settings

# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Validate API key from request header.

    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API Key required. Please provide X-API-Key header."
        )

    if api_key != settings.AI_WORKER_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key"
        )

    return api_key


async def keep_llm_warm():
    """
    Background task that pings the LLM service every 5 minutes
    to prevent cold starts and keep the service responsive.
    """
    logger.info("Starting LLM keep-warm background task")
    while True:
        try:
            logger.info("Pinging LLM service to keep it warm...")
            success = ping_llm()
            if success:
                logger.info("LLM service ping successful")
            else:
                logger.warning("LLM service ping failed")
            await asyncio.sleep(300)  # 5 minutes
        except asyncio.CancelledError:
            logger.info("Keep-warm task cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in keep-warm task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Starts background task on startup and cleanly shuts it down on exit.
    """
    # Startup: Create and start the keep-warm background task
    keep_warm_task = asyncio.create_task(keep_llm_warm())
    logger.info("Application started with LLM keep-warm task")

    yield

    # Shutdown: Cancel the background task
    logger.info("Shutting down, cancelling keep-warm task")
    keep_warm_task.cancel()
    try:
        await keep_warm_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)
app.title = "Reflexion Journal - AI Worker"
app.version = "0.0.1"

@app.get("/",
         tags=["Root"],
         summary="Welcome Endpoint",
         description="Returns a welcome message including the application title and version.")
def root():
    return {"message": f"Welcome to {app.title} v{app.version}"}


@app.get("/ping",
         tags=["Health"],
         summary="Ping Endpoint",
         description="Lightweight ping endpoint for keep-warm checks. Returns immediately without checking LLM service.")
def ping():
    """
    Simple ping endpoint for keep-warm functionality.

    This endpoint provides a fast response without checking downstream services,
    making it suitable for frequent health checks to prevent cold starts.

    Returns:
        - 200 OK with pong message
    """
    return {"status": "ok", "message": "pong"}


@app.get("/health",
         tags=["Health"],
         summary="Health Check",
         description="Checks if the service and LLM inference service are ready to handle requests.")
def health_check():
    """
    Health check endpoint that verifies both this service and the LLM inference service are operational.

    Returns:
        - 200 OK if LLM service is responding
        - 503 Service Unavailable if LLM service is not ready
    """
    llm_ready = ping_llm()

    if llm_ready:
        return {
            "status": "healthy",
            "llm_service": "ready"
        }
    else:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "llm_service": "not ready"
            }
        )


@app.post("/analyze",
          tags=["Analysis"],
          summary="Analyze Reflection",
          description="Analyzes a reflection question and answer pair, extracting themes, sentiment, and beliefs with challenge questions. Requires API key authentication.",
          response_model=LLMEntryAnalysis)
def analyze_reflection_endpoint(
    reflection: QnAPair = Body(
        description="A reflection entry containing a question and its corresponding answer to be analyzed",
        examples=[
            {
                "question": "What did I accomplish today?",
                "answer": "Finished the API integration and deployed to staging. Took longer than expected due to auth issues."
            }
        ]
    ),
    api_key: str = Security(verify_api_key)
):
    result = analyze_reflection(reflection)

    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze reflection. Please check logs for details."
        )
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
