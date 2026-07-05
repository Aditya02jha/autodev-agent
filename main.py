from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import uvicorn
from uuid import uuid4
from brain import index_codebase, get_answer
from planner import create_plan
from models import TaskRequest, PlanRequest, ApplyRequest
from fastapi.middleware.cors import CORSMiddleware


# In-memory sandbox — stores pending changes before apply
pending_sandbox: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Index the codebase on startup so /ask, /plan, /execute are ready immediately
    # index_codebase()
    yield
    # Nothing to clean up on shutdown


app = FastAPI(
    title="AutoDev Agent",
    description="AI agent that understands and modifies a Java Spring Boot codebase.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "AutoDev Agent is online"}


@app.get("/ask")
def ask(q: str):
    """
    Q&A endpoint — ask anything about the codebase.
    Example: GET /ask?q=What controllers exist?
    """
    answer = get_answer(q)
    return {"question": q, "answer": answer}


@app.post("/plan")
def plan(body: PlanRequest):
    """
    Planning endpoint — returns which files need changing and why,
    without making any actual code changes.

    Use this to review the plan before committing to /execute.
    """
    result = create_plan(body.ticket)
    return {
        "ticket_id": body.ticket_number,
        "ticket": body.ticket,
        **result.model_dump(),
    }


@app.post("/generate")
def generate(body: TaskRequest):
    """
    Runs plan + code generation but does NOT write files.
    Returns a sandbox_id and the list of proposed changes for the UI to display.
    """
    from brain import generate_changes_only   
    changes = generate_changes_only(body.task)
    sandbox_id = str(uuid4())
    pending_sandbox[sandbox_id] = changes
    return {"sandbox_id": sandbox_id, "changes": changes["changes"]}


@app.post("/apply/{sandbox_id}")
def apply(sandbox_id: str, body: ApplyRequest):
    """
    User clicked Apply — NOW write files to disk and run Maven.
    """
    if sandbox_id not in pending_sandbox:
        raise HTTPException(404, "Sandbox not found or already applied")
    all_changes = pending_sandbox.pop(sandbox_id)
 
    # Filter to approved subset (if the frontend sends indices)
    if body.approved_indices is not None:
        approved = [all_changes[i] for i in body.approved_indices if i < len(all_changes)]
    else:
        approved = all_changes   # apply everything if no filter sent
 
    from brain import write_and_build
    result = write_and_build(approved)
    return result


@app.delete("/sandbox/{sandbox_id}")
def reject(sandbox_id: str):
    """User rejected — clear the sandbox, nothing was written."""
    pending_sandbox.pop(sandbox_id, None)
    return {"status": "rejected"}

@app.post("/index")
def reindex():
    """Trigger a fresh index of the codebase (also runs on startup)."""
    from brain import index_codebase
    index_codebase()
    return {"status": "indexed"}

# @app.post("/execute")
# def execute_task(body: TaskRequest):
#     """
#     Full pipeline endpoint:
#     1. Runs the planner (finds affected files)
#     2. Reads complete file contents from disk
#     3. Asks Gemini to generate new code
#     4. Writes files to disk
#     5. Runs Maven (with one auto-retry on build failure)

#     Body: { "task": "Create an API endpoint that lists employees with birthdays today" }
#     """
#     result = execute_developer_task(body.task)

#     if result.get("status") == "Error":
#         raise HTTPException(status_code=500, detail=result)

#     return result


# ── Future: human-in-the-loop approve/reject ─────────────────────────────────
# Uncomment these once you build the executers module.
# The flow would be: /execute returns a pending_id → human reviews diff →
# calls /accept/{id} or /reject/{id} → only then files are written.
#
# @app.post("/accept/{execution_id}")
# def accept(execution_id: str):
#     from executers import accept_execution
#     return accept_execution(execution_id)
#
# @app.post("/reject/{execution_id}")
# def reject(execution_id: str):
#     from executers import reject_execution
#     return reject_execution(execution_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)