# 🏗️ System Architecture

This document provides a high-level overview of the AI Council system architecture.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                       │
│  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌────────────┐  │
│  │  Search  │  │  Unified  │  │  Model    │  │  History   │  │
│  │   Bar    │  │  Answer   │  │   Cards   │  │  Sidebar   │  │
│  └──────────┘  └───────────┘  └───────────┘  └────────────┘  │
│                           │  ▲                                    │
│                           │  │ (SSE / WebSocket)                  │
│                           ▼  │                                    │
├──────────────────────────────────────────────────────────────────┤
│                      BACKEND (FastAPI)                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │Orchestrator │  │   Consensus  │  │  Session / Token Mgr   │  │
│  │ (Fan-Out/   │  │  Algorithms  │  │  (Auth + LMArena)      │  │
│  │  Fan-In)    │  │              │  │                         │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│          │               │                    │                   │
│          └───────────────┼────────────────────┘                   │
│                          ▼                                       │
│                ┌─────────────────────┐                           │
│                │  LMArenaBridge      │                           │
│                │  (OpenAI-API Proxy) │                           │
│                └─────────────────────┘                           │
│                          │                                       │
│                          ▼ (WebSocket)                           │
├──────────────────────────────────────────────────────────────────┤
│                      EXTERNAL (LMArena.ai)                       │
│  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐       │
│  │Claude │  │ChatGPT│  │Gemini │  │DeepSeek│  │ Qwen  │       │
│  └───────┘  └───────┘  └───────┘  └───────┘  └───────┘       │
├──────────────────────────────────────────────────────────────────┤
│                        DATABASE (PostgreSQL)                     │
│  ┌────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   Users    │  │ Council Sessions │  │  Model Responses   │  │
│  └────────────┘  └─────────────────┘  └─────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow (User Query to Final Answer)

1.  **User Input**: Frontend → WebSocket connection to Backend.
2.  **Parallel Requests**: Backend → LMArenaBridge (concurrent `POST` requests).
3.  **Model Generation**: LMArenaBridge ↔ LMArena.ai (WebSocket).
4.  **Token Streaming**: LMArenaBridge → Backend → Frontend (each model streams independently).
5.  **Collection**: Backend gathers all full responses.
6.  **Synthesis**: Backend sends all responses to Chairman model via LMArenaBridge.
7.  **Final Stream**: Chairman streams final answer to Frontend.
8.  **Persistence**: Backend stores the entire session in PostgreSQL.

## Scalability Considerations

- **Horizontal Scaling**: Backend is stateless; can run multiple instances behind a load balancer.
- **Session Stickiness**: WebSocket connections need sticky sessions (or use Redis pub/sub for broadcast).
- **Database Pooling**: Use PgBouncer for connection pooling.
- **LMArenaBridge Pool**: Run multiple LMArenaBridge instances with different tokens for load balancing.

## Security Boundaries

- **DMZ**: Frontend and Backend are separated by CORS and API gateway.
- **Secrets**: LMArena token stored in Backend environment, never exposed to Frontend.
- **Database**: Private subnet, only accessible by Backend.
