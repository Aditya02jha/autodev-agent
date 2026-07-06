from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import uvicorn
from brain import index_codebase, get_answer
from planner import create_plan
from models import TaskRequest, PlanRequest, ApplyRequest
from fastapi.middleware.cors import CORSMiddleware
import storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the sqlite tables if they don't exist yet, and sweep out any
    # sandboxes that were left pending past their TTL (e.g. server was
    # restarted mid-review, or the tab was closed and never came back).
    storage.init_db()
    storage.cleanup_expired_sandboxes()
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
    Persists the proposed changes and returns a sandbox_id for the UI to
    display, review, and later apply or reject.
    """
    from brain import generate_changes_only

    storage.cleanup_expired_sandboxes()

    result = generate_changes_only(body.task)
    sandbox_id = storage.save_sandbox(
        task=body.task,
        plan_summary=result.get("plan_summary", ""),
        changes=result["changes"],
    )
    return {
        "sandbox_id": sandbox_id,
        "plan_summary": result.get("plan_summary", ""),
        "changes": result["changes"],
    }


@app.get("/sandbox/{sandbox_id}")
def get_sandbox(sandbox_id: str):
    """
    Rehydrate a pending sandbox — used by the frontend on page load/refresh
    so an in-progress review isn't lost just because the tab was reloaded.
    """
    sandbox = storage.get_sandbox(sandbox_id)
    if not sandbox or sandbox["status"] != "pending":
        raise HTTPException(404, "Sandbox not found or already resolved")
    return sandbox


@app.post("/apply/{sandbox_id}")
def apply(sandbox_id: str, body: ApplyRequest):
    """
    User clicked Apply — NOW write files to disk and run Maven.
    """
    sandbox = storage.get_sandbox(sandbox_id)
    if not sandbox or sandbox["status"] != "pending":
        raise HTTPException(404, "Sandbox not found or already applied")

    all_changes = sandbox["changes"]

    # Filter to approved subset (if the frontend sends indices)
    if body.approved_indices is not None:
        approved = [all_changes[i] for i in body.approved_indices if i < len(all_changes)]
    else:
        approved = all_changes  # apply everything if no filter sent

    from brain import write_and_build
    result = write_and_build(approved)

    build_passed = bool(result.get("maven_results")) and all(
        isinstance(r, str) and "BUILD SUCCESS" in r
        for r in result["maven_results"].values()
    )

    history_entry = storage.add_history_entry(
        ticket=sandbox["task"],
        files_changed=len(approved),
        status="passed" if build_passed else "failed",
        result=result,
        sandbox_id=sandbox_id,
    )

    # The sandbox has been resolved — remove it so it can't be re-applied,
    # but the outcome now lives permanently in the history table.
    storage.delete_sandbox(sandbox_id)

    return {**result, "history_entry": history_entry}


@app.delete("/sandbox/{sandbox_id}")
def reject(sandbox_id: str):
    """User rejected — clear the sandbox, nothing was written."""
    storage.delete_sandbox(sandbox_id)
    return {"status": "rejected"}


@app.get("/history")
def history(limit: int = 200):
    """Full run history, most recent first — persisted, survives restarts."""
    return {"history": storage.get_history(limit=limit)}


@app.delete("/history")
def clear_history():
    """Clear all persisted run history."""
    storage.clear_history()
    return {"status": "cleared"}


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
