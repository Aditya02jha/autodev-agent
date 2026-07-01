from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from brain import index_codebase, get_answer, execute_developer_task
from planner import create_plan
# from executers import execute_plan, accept_execution, reject_execution


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
def plan(ticket: str , ticket_number:str):

    result = create_plan(ticket).model_dump()
    

    return {
        "ticket_id":ticket_number,
        **result
    }

@app.post("/execute")
def execute_task(task: str):
    # This is where the magic happens
    result = execute_developer_task(task)
    return result

# @app.post("/execute")
# def execute():
# # need to change this file path
#     file_path = ("sample.txt")  

#     new_content = ("new content")

#     return execute_plan(file_path,new_content)

# @app.post("/accept/{execution_id}")
# def accept(execution_id: str):

#     return accept_execution(
#         execution_id
#     )

# @app.post("/reject/{execution_id}")
# def reject(execution_id: str):

#     return reject_execution(
#         execution_id
#     )



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)