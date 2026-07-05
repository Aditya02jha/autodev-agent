import os
from langchain_google_genai import ChatGoogleGenerativeAI
from brain import get_context
from models import ChangePlan


def create_plan(ticket_description: str) -> ChangePlan:
    """
    Call 1 — Planner.
    Uses ChromaDB to find relevant chunks, then asks Gemini to decide
    WHICH files need changing and WHY, returning a structured ChangePlan.

    The key fix here is telling the model to return `full_path` (the absolute
    path visible in the FILE: headers of the context) so the executor can
    read the actual file from disk instead of guessing.
    """
    context = get_context(ticket_description)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    )

    structured_llm = llm.with_structured_output(ChangePlan)

    prompt = f"""
    You are a senior software architect analyzing a Java Spring Boot project.

    TASK:
    {ticket_description}

    REPOSITORY CONTEXT (each block starts with FILE: <absolute_path>):
    {context}

    YOUR JOB:
    1. Identify every file that must be created or modified to complete the task.
    2. For each file, provide:
    - `file`: just the filename (e.g. EmployeeService.java)
    - `full_path`: the EXACT absolute path shown in the FILE: header above
        (e.g. C:/Users/adity/.../EmployeeService.java).
        If the file does not exist yet (needs to be created), construct the
        correct path following the same package structure as existing files.
    - `reason`: one sentence explaining why this file needs to change.
    3. Write a short `summary` of what the overall change does.
    4. List high-level `changes` (one item per logical step).

    IMPORTANT: copy `full_path` values exactly from the FILE: headers — do not
    shorten or alter them.
    """

    return structured_llm.invoke(prompt)