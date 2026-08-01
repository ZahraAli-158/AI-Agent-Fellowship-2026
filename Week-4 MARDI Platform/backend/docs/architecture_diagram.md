# Architecture Diagram

GitHub renders the Mermaid diagram below natively when this file is viewed
in the repo — no external image needed.

## System Architecture

```mermaid
graph TB
    subgraph Frontend["React Frontend (Vite)"]
        UI[Dashboard UI]
        Sidebar[Sidebar: Runs / Reports / Settings]
        Tabs[Overview / Tasks / Evidence / Analysis / Log / State / Report / Analytics]
        UI --> Sidebar
        UI --> Tabs
    end

    subgraph Backend["FastAPI Backend"]
        API[REST API Layer<br/>app/api.py]
        Graph[LangGraph Workflow<br/>app/graph/]
        Agents[5 Agents<br/>app/agents/]
        Tools[Tools<br/>app/tools/]
        Schemas[Pydantic Schemas<br/>app/schemas/]
        LLMClient[LLM Client<br/>mock / Gemini / Anthropic]
        Corpus[(Local Research Corpus<br/>app/storage/corpus)]

        API --> Graph
        Graph --> Agents
        Agents --> Tools
        Agents --> Schemas
        Agents --> LLMClient
        Tools --> Corpus
    end

    subgraph External["External Services"]
        Gemini[Google Gemini API]
        Anthropic[Anthropic API]
    end

    UI <-->|"REST + polling"| API
    LLMClient -.->|live mode| Gemini
    LLMClient -.->|live mode| Anthropic

    style Frontend fill:#6366f1,color:#fff
    style Backend fill:#14b8a6,color:#fff
    style External fill:#94a3b8,color:#fff
```

## Layered View

```mermaid
graph LR
    A[User] --> B[React Dashboard]
    B --> C[FastAPI REST API]
    C --> D[LangGraph Orchestration]
    D --> E[Supervisor]
    D --> F[Researcher x N parallel]
    D --> G[Analyst]
    D --> H[Critic]
    D --> I[Writer]
    E --> J[(Shared WorkflowState)]
    F --> J
    G --> J
    H --> J
    I --> J
```

## Component responsibilities

| Layer | Responsibility |
|---|---|
| React Frontend | Live dashboard — polls the backend, renders task plan/evidence/report/analytics, surfaces human checkpoints |
| FastAPI `app/api.py` | REST layer — starts/tracks runs on background threads, exposes 10 endpoints (see `backend/README.md`) |
| LangGraph `app/graph/` | Orchestration — state model, routing/conditional edges, human checkpoint blocking |
| Agents `app/agents/` | The 5 specialized roles (Supervisor, Researcher, Analyst, Critic, Writer) |
| Tools `app/tools/` | Search, extraction, evidence storage/retrieval, calculator |
| Schemas `app/schemas/` | Pydantic models — Task, Evidence, AnalysisOutput, CriticFeedback, FinalReport |
| LLM Client `app/services/llm_client.py` | Swappable mock / Gemini / Anthropic backend, with a hard timeout |
