# AI Workspace Platform

A multi-user AI Workspace Platform designed as a university capstone project. The platform provides workspace management, configurable AI assistants, persistent chat, document-grounded question answering, long-term memory, prompt management, reusable AI skills, dashboard analytics, and multiple LLM provider support.

## 1. Problem Statement

Modern AI tools often separate conversations, documents, prompts, memory, and productivity workflows across different applications. This makes it difficult for users and teams to maintain context and organize AI-assisted work.

The AI Workspace Platform addresses this problem by providing a centralized workspace where users can create workspaces, configure AI assistants, communicate with multiple LLM providers, upload and query documents using RAG, maintain long-term memory, manage reusable prompts, and execute specialized AI skills from one platform.

The platform also provides a built-in Mock Provider so that the core application can operate when an external LLM API key is unavailable.

## 2. Features

### Workspace Management
- User registration and authentication
- Create and manage multiple workspaces
- Edit workspace information
- Clone workspaces
- Archive and restore workspaces
- Workspace sharing

### AI Assistant Configuration
- Create and configure AI assistants
- Configure assistant names and system prompts
- Configure model parameters such as temperature
- Save assistant configurations
- Live assistant preview

### Persistent Chat
- Create conversations
- Select AI assistants
- Send and receive AI messages
- Conversation history
- Conversation search
- Message pinning
- Conversation export
- Model and token information
- Response-time information

### LLM Providers
The platform supports pluggable LLM providers:
- Google Gemini
- OpenAI
- Anthropic
- Mock Provider / offline fallback

### Knowledge Base / RAG
- Upload PDF, DOCX, TXT, and Markdown documents
- Document processing and chunking
- Embedding generation
- Semantic search
- Grounded question answering
- Document summaries
- Source citations

### Long-Term Memory
- Add memory items
- Categorize memories
- Pin and unpin memories
- Search memories
- Edit and delete memories
- Recall stored information through Chat

### Prompt Library
- Create prompts
- Edit prompts
- Delete prompts
- Duplicate prompts
- Favorite prompts
- Filter favorites
- Search prompts
- Category filtering
- Database persistence
- Use prompts directly in Chat

### AI Skills
The platform provides 10 reusable AI skills:
1. Research
2. Summarization
3. Email Generator
4. Report Generator
5. Meeting Notes
6. Task Planner
7. SWOT Generator
8. Business Canvas
9. Code Review
10. Idea Generator

### Dashboard and Advanced Features
- Workspace activity dashboard
- Usage and conversation metrics
- Dark/light theme
- Conversation export
- Voice input
- Speech output
- Pinned messages
- Workspace sharing

## 3. Technology Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Pytest

### Frontend
- Python
- Streamlit

### Database
- SQLite
- PostgreSQL-compatible architecture

### AI / LLM
- Google Gemini
- OpenAI
- Anthropic
- Mock Provider

### Knowledge Base
- Document extractors
- Text chunking
- Embeddings
- Semantic search
- Retrieval-Augmented Generation (RAG)

### Development & Deployment
- Docker
- Docker Compose
- Uvicorn
- Render
- Streamlit Community Cloud

## 4. Architecture

The application follows a modular frontend/backend architecture.

```text
                    ┌─────────────────────────┐
                    │     Streamlit Frontend  │
                    │                         │
                    │ Dashboard               │
                    │ Chat                    │
                    │ Knowledge Base          │
                    │ Memory                   │
                    │ Prompt Library           │
                    │ AI Skills               │
                    │ Assistant Settings      │
                    └────────────┬────────────┘
                                 │
                              API Calls
                                 │
                    ┌────────────▼────────────┐
                    │       FastAPI Backend   │
                    │                         │
                    │ Authentication          │
                    │ Workspaces              │
                    │ Assistants              │
                    │ Conversations           │
                    │ Memory                  │
                    │ Prompt Management       │
                    │ Skills                  │
                    │ Knowledge/RAG            │
                    └───────┬─────────┬───────┘
                            │         │
                 ┌──────────▼───┐ ┌──▼────────────────┐
                 │   Database   │ │   LLM Provider    │
                 │   SQLite    │ │ Factory            │
                 │             │ │ Gemini             │
                 │ SQLAlchemy  │ │ OpenAI             │
                 └─────────────┘ │ Anthropic          │
                                 │ Mock               │
                                 └────────────────────┘
```

The backend contains API routers, configuration and security components, database models, schemas, LLM services, knowledge/RAG services, chat orchestration, and the AI skills registry.

The frontend contains the main application shell, navigation, theme handling, reusable UI components, API client, and pages for Dashboard, Chat, Knowledge Base, Memory, Prompt Library, AI Skills, and Assistant Settings.

An architecture diagram is also available at:

`docs/diagrams/architecture_diagram.svg`

## 5. Installation

### Prerequisites

- Python 3.x
- Git
- An LLM API key if real external LLM responses are required
- Docker (optional)

### Backend

```bash
cd backend
python -m venv venv
```

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the environment file:

```bash
cp .env.example .env
```

On Windows, the equivalent can be:

```powershell
Copy-Item .env.example .env
```

Add at least one provider API key to `.env` if real external LLM responses are required.

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

Open a new terminal:

```bash
cd frontend
python -m venv venv
```

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Streamlit:

```bash
streamlit run app.py
```

Open:

`http://localhost:8501`

The interactive backend API documentation is available at:

`http://localhost:8000/docs`

and:

`http://localhost:8000/redoc`

The application can also operate end-to-end with the built-in Mock Provider when no external API key is configured.

## 6. Deployment

The project supports deployment using:

- Render for the FastAPI backend
- Streamlit Community Cloud for the frontend
- Docker Compose for self-hosting

The deployment guide is available at:

`docs/7_Deployment_Guide.docx`

### Docker

The project includes:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

A self-hosted deployment can be started with:

```bash
docker compose up --build
```

### Live Deployment Status

A live public URL should only be listed here after an actual deployment has been completed and verified.

**Current documented status:** deployment configuration and instructions are provided; a live URL must be added after successful deployment.

## 7. API Endpoints

The backend exposes REST API endpoints through FastAPI.

The project contains API documentation generated from the OpenAPI schema:

`docs/api/API_DOCUMENTATION.md`

and:

`docs/api/openapi.json`

The documented API contains **48 endpoints**.

The API is organized around major resources including:

- Authentication
- Workspaces
- Assistants
- Conversations
- Messages
- Documents / Knowledge Base
- Memory
- Prompts
- AI Skills
- Dashboard
- Workspace sharing
- Export functionality

For the complete endpoint definitions, request schemas, response schemas, and authentication requirements, refer to the generated API documentation and the interactive Swagger UI.

## 8. Database

The application uses **SQLite** through SQLAlchemy, with a PostgreSQL-compatible architecture.

The backend contains:

```text
backend/app/db/
backend/app/models/
```

The project includes 12 SQLAlchemy models.

The database layer is responsible for persistent application data such as:

- Users
- Workspaces
- Assistants
- Conversations
- Messages
- Documents
- Memory
- Prompts
- Skills
- Related workspace/application data

The database Entity Relationship Diagram is available at:

`docs/diagrams/database_erd.svg`

The project excludes local database files from Git using `.gitignore`.

## 9. Screenshots

Screenshots were captured through manual testing of the running application and should be stored in:

`docs/screenshots/`

The screenshot set covers the major application workflows, including:

1. Login/Register
2. Dashboard
3. Chat with an active conversation
4. Assistant Settings with Live Preview
5. Knowledge Base with uploaded document
6. Memory
7. Prompt Library
8. AI Skills with generated result
9. Workspace management options
10. Dark Mode
11. Light Mode

These screenshots provide visual evidence of the implemented functionality and should be included with the final project submission.

## 10. Evaluation Results

### Automated Tests

The project includes a backend test suite containing **51 pytest tests**.

Run the tests with:

```bash
cd backend
pytest tests/ -v
```

The documented test suite covers:

- Authentication
- Workspaces
- Assistants
- Chat
- Documents and RAG
- Memory
- Prompts
- AI Skills
- Dashboard
- Export
- Workspace sharing
- Workspace clone/archive
- Message pinning
- LLM provider factory
- Mock fallback
- Memory recall in Chat

### Evaluation Scenarios

The project includes an evaluation dataset containing **44 scenarios**:

`docs/evaluation/evaluation_dataset.json`

Evaluation results are documented in:

`docs/evaluation/evaluation_results.md`

### Manual Functional Testing

Manual testing was also performed across the major modules.

The following areas were verified:

| Module | Status |
|---|---|
| Authentication | ✅ Passed |
| Workspace Management | ✅ Passed |
| Assistant Configuration | ✅ Passed |
| Persistent Chat | ✅ Passed |
| Gemini Integration | ✅ Passed |
| Knowledge Base / RAG | ✅ Passed |
| Document Intelligence | ✅ Passed |
| Long-Term Memory | ✅ Passed |
| Prompt Library | ✅ Passed after fixes |
| AI Skills | ✅ Passed |
| Dashboard | ✅ Tested |
| Workspace Sharing | ✅ Tested |
| Voice Input | ✅ Tested |
| Speech Output | ✅ Tested |
| Dark Mode Persistence | ✅ Fixed and tested |
| Error Handling / Mock Fallback | ✅ Passed |

### Issues Fixed During Testing

#### Prompt Library — Use in Chat

The prompt could initially be loaded into Chat, but sending/response behavior was inconsistent.

The workflow was subsequently fixed and retested.

**Final Status: ✅ Resolved**

#### Dark Mode Persistence

The selected dark theme could previously turn off during navigation or refresh.

Theme persistence was subsequently implemented and tested.

**Final Status: ✅ Resolved**

#### LLM Provider Selection

The application could previously fall back to the Mock Provider when Gemini was intended to be configured.

The provider configuration/factory was corrected and real Gemini responses were successfully verified when the API configuration was available.

**Final Status: ✅ Resolved**

## 11. Future Improvements

Potential future improvements include:

- Add a verified public deployment and production live URL.
- Add stronger production-grade authentication and authorization controls.
- Expand automated test coverage beyond the current test suite.
- Improve performance monitoring and load testing under larger workloads.
- Add more advanced document formats and multimodal document understanding.
- Improve RAG retrieval and ranking for larger knowledge bases.
- Add more LLM providers and model-selection controls.
- Add richer workspace collaboration and permission management.
- Improve voice interaction and speech capabilities.
- Add advanced analytics and usage reporting.
- Introduce production PostgreSQL deployment for larger-scale usage.
- Add more reusable AI Skills and customizable workflows.
- Improve mobile responsiveness and accessibility.
- Add stronger production observability, logging, and monitoring.

## Project Documentation

The project contains the following supporting documentation:

| Document | Location |
|---|---|
| Architecture Documentation | `docs/1_Architecture_Documentation.docx` |
| Architecture Diagram | `docs/diagrams/architecture_diagram.svg` |
| Database ERD | `docs/diagrams/database_erd.svg` |
| Research Report | `docs/2_Research_Report.docx` |
| Evaluation Framework | `docs/3_Evaluation_Framework.docx` |
| Experiments | `docs/4_Experiments.docx` |
| Security Review | `docs/5_Security_Review.docx` |
| Performance Analysis | `docs/6_Performance_Analysis.docx` |
| Deployment Guide | `docs/7_Deployment_Guide.docx` |
| API Documentation | `docs/api/API_DOCUMENTATION.md` |
| OpenAPI Specification | `docs/api/openapi.json` |
| Evaluation Dataset | `docs/evaluation/evaluation_dataset.json` |
| Evaluation Results | `docs/evaluation/evaluation_results.md` |
| Builder Journal | `docs/BUILDER_JOURNAL.md` |
| Screenshots | `docs/screenshots/` |

## Security Note

Never commit real API keys or secrets to the repository.

The project's `.gitignore` excludes:

- `.env`
- `*.db`
- `uploads/`
- `vector_store/`

API keys should always be stored through environment variables or an appropriate deployment secret-management mechanism.

## Conclusion

The AI Workspace Platform provides a centralized environment for AI-assisted productivity, combining workspace management, configurable assistants, persistent conversations, document-grounded RAG, long-term memory, prompt reuse, and reusable AI Skills.

The project has been manually tested across its major functional modules and includes automated tests, evaluation scenarios, architecture and API documentation, security/performance documentation, deployment instructions, and visual testing evidence.

The platform is prepared for final submission, subject to verification of deployment/live URL information and any remaining assignment-specific evidence.
