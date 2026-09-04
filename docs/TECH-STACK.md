# 🧰 Technology Stack

This document lists the exact technologies used in the AI Council project, with rationale.

## Frontend

| Technology | Version | Purpose |
| :--- | :--- | :--- |
| Next.js | 14.x | React framework with server-side rendering, file-based routing, and API routes. |
| React | 18.x | UI library for building component-based interfaces. |
| TypeScript | 5.x | Strict type safety and better developer experience. |
| Tailwind CSS | 3.x | Utility-first CSS framework for rapid UI development. |
| Vercel AI SDK | 3.x | Handles SSE streaming from the backend to React components. |
| Zustand | 4.x | Lightweight state management for council session state. |
| React Hook Form | 7.x | Manage form inputs (search bar, settings) efficiently. |

## Backend

| Technology | Version | Purpose |
| :--- | :--- | :--- |
| FastAPI | 0.115.x | High-performance Python async framework for the orchestration API. |
| Python | 3.11+ | Runtime. |
| Uvicorn | 0.30.x | ASGI server for running FastAPI in production. |
| Websockets | 11.x | For low-latency bidirectional streaming with LMArenaBridge. |
| SQLAlchemy | 2.x | ORM for database operations (async support). |
| Alembic | 1.13.x | Database migration management. |
| Pydantic | 2.x | Data validation and settings management. |
| httpx | 0.27.x | Async HTTP client for calling LMArenaBridge. |
| python-dotenv | 1.x | Load environment variables from `.env`. |

## AI Gateway

| Technology | Version | Purpose |
| :--- | :--- | :--- |
| LMArenaBridge | latest | OpenAI-compatible API bridge to LMArena.ai. Uses FastAPI + WebSockets internally. |

## Database

| Technology | Version | Purpose |
| :--- | :--- | :--- |
| PostgreSQL | 15+ | Relational database for users, conversations, and analytics. |
| Redis | 7.x | (Optional) Caching layer for frequently asked queries. |

## DevOps & Infrastructure

| Technology | Purpose |
| :--- | :--- |
| Docker | Containerization for consistent development and deployment. |
| Docker Compose | Orchestrate multi-container services. |
| GitHub Actions | CI/CD pipeline for automated testing and deployment. |
| Vercel | Frontend hosting (optional). |
| AWS EC2 / ECS | Backend hosting (optional). |
| Prometheus + Grafana | Monitoring and observability (Phase 3). |

## Testing

| Technology | Purpose |
| :--- | :--- |
| Pytest | Python unit and integration tests. |
| Jest / React Testing Library | Frontend component testing. |
| Playwright | End-to-end browser testing (ironic but effective). |
