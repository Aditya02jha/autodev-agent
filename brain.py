import os
import shutil
import json
from collections import defaultdict
from dotenv import load_dotenv

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document

from tools import write_file, run_maven_test

load_dotenv()

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

CHROMA_PATH = "./chroma_db"

ALLOWED_EXTENSIONS = {
    ".java", ".xml", ".yml", ".yaml", ".properties",
    ".sql", ".md", ".txt", ".json",
    ".js", ".ts", ".jsx", ".tsx",
    ".py", ".php", ".go", ".tf",
}

SKIP_DIRS = {
    ".git", ".idea", "node_modules", "target",
    "build", "__pycache__", ".venv", ".mvn",
}


# ─────────────────────────────────────────────
# Indexing
# ─────────────────────────────────────────────

def index_codebase():
    path = os.getenv("PROJECT_ROOT_PATH")
    if not path:
        raise Exception("PROJECT_ROOT_PATH not configured in .env")

    print(f"--- Indexing started for: {path} ---")

    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    documents = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if not content.strip():
                    continue
                documents.append(
                    Document(
                        page_content=content,
                        metadata={"source": full_path, "filename": file, "extension": ext},
                    )
                )
            except Exception as e:
                print(f"Skipping {full_path}: {e}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)
    chunks = splitter.split_documents(documents)

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH,
    )

    print(f"--- Indexing complete: {len(documents)} files / {len(chunks)} chunks ---")


# ─────────────────────────────────────────────
# Context retrieval (used by planner & Q&A)
# ─────────────────────────────────────────────

def get_context(query: str) -> str:
    """
    Returns relevant code chunks from ChromaDB formatted as
    FILE: <path>\\n<content>\\n===...
    Used by the planner to discover which files exist.
    """
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 20, "fetch_k": 100},
    )
    docs = retriever.invoke(query)

    parts = []
    for doc in docs:
        source = doc.metadata.get("source", "Unknown")
        parts.append(f"FILE: {source}\n{doc.page_content}\n{'=' * 50}")
    return "\n".join(parts)


def read_full_file(path: str) -> str:
    """Read the COMPLETE content of a file from disk (not from ChromaDB chunks)."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        return ""   # new file — executor will create it


# ─────────────────────────────────────────────
# Q&A
# ─────────────────────────────────────────────

def get_answer(question: str) -> str:
    context = get_context(question)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    )

    prompt = f"""
    You are a senior Spring Boot architect.
    Analyze ALL retrieved files.

    Rules:
    1. Use FILE names and paths from the context.
    2. If asked about controllers, look for @RestController / @Controller / classes ending with Controller.
    3. If the answer is not in context, say so clearly.
    4. List file names and endpoints when relevant.

    CONTEXT:
    {context}

    QUESTION:
    {question}

    ANSWER:
    """
    response = llm.invoke(prompt)
    return response.content


# ─────────────────────────────────────────────
# Executor  ← the main fix
# ─────────────────────────────────────────────
def generate_changes_only(task_description: str) -> dict:
    """
    Runs planner + Gemini code generation.
    Does NOT write any files.
    Returns the generated changes.
    """

    from planner import create_plan

    print("--- Planning ---")
    plan = create_plan(task_description)

    print(f"Plan: {plan.summary}")
    for af in plan.affected_files:
        print(f"[{af.file}] {af.reason}")

    # Build context
    file_contexts = []

    for af in plan.affected_files:
        content = read_full_file(af.full_path)

        if content:
            file_contexts.append(
                f"FILE: {af.full_path}\n"
                f"REASON: {af.reason}\n"
                f"FULL CONTENT:\n{content}\n"
                f"{'=' * 60}"
            )
        else:
            file_contexts.append(
                f"FILE: {af.full_path}\n"
                f"REASON: {af.reason}\n"
                f"[NEW FILE — does not exist yet, create it]\n"
                f"{'=' * 60}"
            )

    full_context = "\n".join(file_contexts)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    )

    prompt = f"""
        You are an AI Developer working on a Java Spring Boot project.

        TICKET:
        {task_description}

        PLAN SUMMARY:
        {plan.summary}

        IMPLEMENTATION STEPS:
        {chr(10).join(f"- {c}" for c in plan.changes)}

        COMPLETE FILE CONTENTS:
        {full_context}

        INSTRUCTIONS:

        - Implement the ticket exactly as described.
        - For every changed file output COMPLETE file content.
        - Preserve unrelated code.
        - Respond ONLY with valid JSON.

        [
        {{
            "file_path": "...",
            "new_content": "...",
            "explanation": "...",
            "service_folder": "..."
        }}
        ]
        """

    response = llm.invoke(prompt)

    raw = (
        response.content
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    data = json.loads(raw)

    if isinstance(data, dict):
        data = [data]

    return {
        "plan_summary": plan.summary,
        "changes": data
    }

def write_and_build(changes: list) -> dict:
    """
    Writes generated files to disk and runs Maven.
    """

    root_path = os.getenv("PROJECT_ROOT_PATH", "")

    results = []

    for item in changes:
        write_result = write_file(
            item["file_path"],
            item["new_content"]
        )

        print(write_result)

        results.append({
            "file": item["file_path"],
            "explanation": item["explanation"]
        })

    service_folders = list(
        {item["service_folder"] for item in changes}
    )

    maven_results = {}

    for folder in service_folders:

        full_service_path = os.path.join(root_path, folder)

        print(f"Running Maven in {full_service_path}")

        maven_results[folder] = run_maven_test(full_service_path)

    return {
        "status": "Applied",
        "files_changed": results,
        "maven_results": maven_results,
    }


# def execute_developer_task(task_description: str) -> dict:
#     """
#     Two-call pipeline:
#     Call 1 (planner)  — find which files need changing (returns ChangePlan)
#     Call 2 (executor) — read FULL file content for each, generate new code

#     After writing all files, runs Maven once per service folder.
#     If Maven fails, retries once with the error fed back to Gemini.
#     """
#     # Import here to avoid circular import (planner imports brain)
#     from planner import create_plan

#     # ── CALL 1: plan ─────────────────────────────────────────────────
#     print("--- Planning ---")
#     plan = create_plan(task_description)
#     print(f"Plan: {plan.summary}")
#     for af in plan.affected_files:
#         print(f"  [{af.file}] {af.reason}")

#     # ── Build full-file context for affected files ────────────────────
#     file_contexts = []
#     for af in plan.affected_files:
#         content = read_full_file(af.full_path)
#         if content:
#             file_contexts.append(
#                 f"FILE: {af.full_path}\nREASON: {af.reason}\n"
#                 f"FULL CONTENT:\n{content}\n{'=' * 60}"
#             )
#         else:
#             # New file that doesn't exist yet
#             file_contexts.append(
#                 f"FILE: {af.full_path}\nREASON: {af.reason}\n"
#                 f"[NEW FILE — does not exist yet, create it]\n{'=' * 60}"
#             )

#     full_context = "\n".join(file_contexts)

#     # ── CALL 2: generate code ─────────────────────────────────────────
#     print("--- Generating code ---")
#     llm = ChatGoogleGenerativeAI(
#         model="gemini-2.5-flash",
#         google_api_key=os.getenv("GEMINI_API_KEY"),
#         temperature=0,
#     )

#     def build_code_prompt(extra_error: str = "") -> str:
#         error_section = f"\nPREVIOUS BUILD ERROR TO FIX:\n{extra_error}\n" if extra_error else ""
#         return f"""
#     You are an AI Developer working on a Java Spring Boot project.

#     TICKET: {task_description}

#     PLAN SUMMARY: {plan.summary}

#     IMPLEMENTATION STEPS:
#     {chr(10).join(f"- {c}" for c in plan.changes)}
#     {error_section}
#     COMPLETE FILE CONTENTS (read carefully before changing anything):
#     {full_context}

#     INSTRUCTIONS:
#     - Implement the ticket exactly as described.
#     - For every file that needs to change, output its COMPLETE new content (not a diff).
#     - Preserve all existing methods/imports that are not related to this ticket.
#     - Respond ONLY with a valid JSON array, no markdown fences:

#     [
#     {{
#         "file_path": "exact/absolute/path/to/File.java",
#         "new_content": "complete file content here",
#         "explanation": "one sentence: what changed and why",
#         "service_folder": "folder containing pom.xml (just the folder name, e.g. management)"
#     }}
#     ]
#     """

#     def call_gemini(prompt: str) -> list:
#         response = llm.invoke(prompt)
#         raw = response.content.replace("```json", "").replace("```", "").strip()
#         data = json.loads(raw)
#         if isinstance(data, dict):
#             data = [data]
#         return data

#     try:
#         data = call_gemini(build_code_prompt())
#     except Exception as e:
#         return {"status": "Error", "message": f"Code generation failed: {e}"}

#     # ── Write files ───────────────────────────────────────────────────
#     results = []
#     root_path = os.getenv("PROJECT_ROOT_PATH", "")

#     for item in data:
#         file_path = item["file_path"]
#         content   = item["new_content"]
#         write_result = write_file(file_path, content)
#         print(write_result)
#         results.append({"file": file_path, "explanation": item["explanation"]})

#     # ── Run Maven per service folder ──────────────────────────────────
#     # Group changed files by service_folder so we don't run Maven multiple
#     # times for the same service when several files change in one task.
#     service_folders = list({item["service_folder"] for item in data})
#     maven_results = {}

#     for folder in service_folders:
#         full_service_path = os.path.join(root_path, folder)
#         print(f"--- Running Maven in: {full_service_path} ---")
#         test_result = run_maven_test(full_service_path)
#         maven_results[folder] = test_result

#         # ── Retry once if build failed ────────────────────────────────
#         build_failed = (
#             isinstance(test_result, dict) and test_result.get("status") == "failed"
#         ) or (
#             isinstance(test_result, str) and "BUILD FAILURE" in test_result
#         )

#         if build_failed:
#             print(f"--- Build failed in {folder}, retrying with error context ---")
#             error_text = str(test_result)
#             try:
#                 retry_data = call_gemini(build_code_prompt(extra_error=error_text))
#                 for item in retry_data:
#                     write_file(item["file_path"], item["new_content"])
#                     results.append({
#                         "file": item["file_path"],
#                         "explanation": f"[RETRY] {item['explanation']}",
#                     })
#                 retry_result = run_maven_test(full_service_path)
#                 maven_results[folder] = {"first_attempt": test_result, "retry": retry_result}
#             except Exception as retry_err:
#                 maven_results[folder] = {
#                     "first_attempt": test_result,
#                     "retry_error": str(retry_err),
#                 }

#     return {
#         "status": "Applied",
#         "plan_summary": plan.summary,
#         "files_changed": results,
#         "maven_results": maven_results,
#     }

