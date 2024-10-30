from fastapi import FastAPI

app = FastAPI()
app.title = "Reflection Journal API"
app.description = "API for the Reflection Journal"
app.version = "0.0.1"


@app.get("/")
async def root():
    return {"message": "Reflection Journal API"}
