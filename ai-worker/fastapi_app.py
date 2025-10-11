# Third-party imports
from fastapi import FastAPI
import uvicorn

app = FastAPI(lifespan=lifespan)
app.title = "Reflexion Journal"
app.version = "0.0.1"

@app.get("/", 
         tags=["Root"], 
         summary="Welcome Endpoint",
         description="Returns a welcome message including the application title and version.")
def root():
    return {"message": f"Welcome to {app.title} v{app.version}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
