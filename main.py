from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from brain import index_codebase, get_answer, execute_developer_task
from planner import create_plan

# This is the modern replacement for @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run indexing on startup
    index_codebase()
    yield
    # Clean up (if needed) on shutdown

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home():
    return {"status": "Master AI is Online"}

@app.get("/ask")
def ask(q: str):
    answer = get_answer(q)
    return {"question": q, "answer": answer}

@app.get("/plan")
def plan(ticket: str):

    result = create_plan(ticket)

    return result.model_dump()

@app.post("/execute")
def execute_task(task: str):
    # This is where the magic happens
    result = execute_developer_task(task)
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)