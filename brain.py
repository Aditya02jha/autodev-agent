import os
import shutil

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document
from tools import write_file, run_maven_test
import json


load_dotenv()

# Use the HuggingFace model for local, free embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
CHROMA_PATH = "./chroma_db"
ALLOWED_EXTENSIONS = {
    ".java",
    ".xml",
    ".yml",
    ".yaml",
    ".properties",
    ".sql",
    ".md",
    ".txt",
    ".json",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".py",
    ".php",
    ".go",
    ".tf"
}
def index_codebase():
    path = os.getenv("PROJECT_ROOT_PATH")
    print(f"--- Indexing started for: {path} ---")
    
    if not path:
        raise Exception("PROJECT_ROOT_PATH not configured")

    # recreate db every indexing run
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    documents = []

    for root, dirs, files in os.walk(path):

        dirs[:] = [
            d for d in dirs
            if d not in {
                ".git",
                ".idea",
                "node_modules",
                "target",
                "build",
                "__pycache__",
                ".venv",
                ".mvn"
            }
        ]

        for file in files:

            ext = os.path.splitext(file)[1].lower()

            if ext not in ALLOWED_EXTENSIONS:
                continue

            full_path = os.path.join(root, file)

            try:
                with open(
                    full_path,
                    "r",
                    encoding="utf-8",
                    errors="ignore"
                ) as f:

                    content = f.read()

                if not content.strip():
                    continue

                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": full_path,
                            "filename": file,
                            "extension": ext
                        }
                    )
                )

            except Exception as e:
                print(f"Skipping {full_path}: {e}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=300
    )

    chunks = splitter.split_documents(documents)

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    )

    print(
        f"--- Indexing complete. "
        f"Indexed {len(documents)} files "
        f"and {len(chunks)} chunks ---"
    )


def get_context(query):

    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )

    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 20,
            "fetch_k": 100
        }
    )

    docs = retriever.invoke(query)

    context_parts = []

    for doc in docs:

        source = doc.metadata.get(
            "source",
            "Unknown"
        )

        context_parts.append(
            f"""
FILE: {source}

{doc.page_content}

=================================================
"""
        )

    return "\n".join(context_parts)


def get_answer(question):

    context = get_context(question)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0
    )

    prompt = f"""
    You are a senior Spring Boot architect.

    Analyze ALL retrieved files.

    Rules:
    1. Use FILE names and paths.
    2. If asked about controllers, search for:
    - @RestController
    - @Controller
    - classes ending with Controller
    3. If the answer is not in context, say so.
    4. List file names and endpoints when possible.

    CONTEXT:
    {context}

    QUESTION:
    {question}

    ANSWER:
    """

    response = llm.invoke(prompt)
    print("=" * 100)
    print(context)
    print("=" * 100)
    return response.content



def execute_developer_task(task_description):
    context = get_context(task_description)
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    prompt = f"""
    You are an AI Developer Master Service.
    TASK: {task_description}
    
    CONTEXT OF EXISTING CODE:
    {context}

    INSTRUCTIONS:
    1. Analyze the context.
    2. Provide the code changes required.
    3. Respond ONLY in the following JSON format — always an ARRAY, even for one file:
    [
      {{
        "file_path": "full/path/to/file.java",
        "new_content": "the complete code for the file",
        "explanation": "what you did",
        "service_folder": "folder_name_where_pom_is"
      }}
    ]
    """

    response = llm.invoke(prompt)

    try:
        json_str = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)

        # normalize — always work with a list
        if isinstance(data, dict):
            data = [data]

        results = []
        root_path = os.getenv("PROJECT_ROOT_PATH")

        for item in data:
            file_path     = item['file_path']
            content       = item['new_content']
            service_folder = item['service_folder']
            explanation   = item['explanation']

            # write the file
            write_result = write_file(file_path, content)
            print(write_result)

            results.append({
                "file": file_path,
                "explanation": explanation
            })

        # run maven ONCE after all files are written
        full_service_path = os.path.join(root_path, data[0]['service_folder'])
        test_result = run_maven_test(full_service_path)

        return {
            "status": "Applied",
            "files_changed": results,
            "test_result": test_result
        }

    except Exception as e:
        return {"status": "Error", "message": str(e), "raw_ai_response": response.content}