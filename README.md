# Repo Engineer

Repo Engineer is an AI-powered software engineering agent that analyzes source code repositories, understands project structure, plans code changes from tickets, and eventually executes those changes automatically.

The long-term goal is:

Ticket → Analysis → Planning → Code Changes → Build/Test → Review

---

## Current Features

### Repository Indexing

The application scans a source code repository and indexes files into ChromaDB using embeddings.

Currently supported file types include:

- Java
- XML
- YAML
- Properties
- JSON
- SQL
- Markdown
- JavaScript
- TypeScript
- Python
- PHP
- Terraform

Excluded folders:

- .git
- target
- build
- node_modules
- .idea
- __pycache__

---

### Repository Q&A

Users can ask questions such as:

- What controllers exist?
- Explain authentication flow.
- Which service calls this repository?
- What endpoints are available?

The system retrieves relevant files from ChromaDB and uses Gemini to answer.

---

### Planning Agent

The planning agent receives a ticket description and determines:

- Which files are likely affected
- Why those files need modification
- High-level implementation steps

Example:

Input:

Add employee search by email.

Output:

- EmployeeController.java
- EmployeeService.java
- EmployeeRepo.java

Along with reasoning and proposed changes.

---

## Planned Features

### File Modification Agent

The agent will:

1. Read complete source files.
2. Generate modifications.
3. Produce code changes.
4. Validate generated code.

---

### Build Validation

After code generation:

- Run Maven/Gradle/NPM tests
- Capture build errors
- Feed errors back into the AI
- Retry until successful

---

### Git Integration

Planned capabilities:

- Create branches
- Generate commits
- Generate pull requests
- Produce diffs for review

---

## Architecture

Current:

Repository
↓
Indexer
↓
ChromaDB
↓
Retriever
↓
Gemini
↓
Answer

Planned:

Ticket
↓
Planner Agent
↓
Affected Files
↓
File Loader
↓
Code Generation Agent
↓
Build/Test Agent
↓
Git Agent
↓
Pull Request

---

## Technology Stack

Backend:
- Python
- FastAPI

AI:
- Google Gemini

Vector Database:
- ChromaDB

Embeddings:
- HuggingFace Embeddings

Future:
- Git Integration
- Build Validation
- Multi-Agent Workflow

---

## Project Goals

The project is not intended to be a chatbot.

The objective is to build an autonomous software engineering agent capable of:

- Understanding large repositories
- Analyzing tickets
- Planning changes
- Modifying source code
- Running tests
- Producing production-ready pull requests

while keeping a human-in-the-loop approval process.

---

## Important Constraints

- Never modify files without explicit approval.
- Prefer reading complete files over isolated chunks when generating code.
- Repository analysis should be based on actual source code rather than assumptions.
- Build validation must occur before accepting generated changes.
- The planner should identify affected files before any code generation begins.

---

## Development Roadmap

Phase 1
- Repository indexing
- Repository Q&A
- Planning agent

Phase 2
- File loading engine
- Change generation

Phase 3
- Build/test validation

Phase 4
- Git integration

Phase 5
- Autonomous ticket implementation

  Screenshots
  <img width="1770" height="725" alt="image" src="https://github.com/user-attachments/assets/336f549b-ed36-46b5-a4cf-51f91893f742" />

