# 🗄️ Database Schema

This document describes the database design for the AI Council (sqlite `aicouncil.db` for dev, PostgreSQL for prod — same schema).

> **Auth simplified (Sept 2026):** No website login. The `users` table exists for future private deploys but is **unused** in the default flow — `council_sessions.user_id` is always `null` (anonymous). Only LMArena login is required.

## Entity Relationship Diagram (ERD)

```
┌─────────────────┐       ┌─────────────────────┐
│      users       │       │  council_sessions   │
├─────────────────┤       ├─────────────────────┤
│ id (PK)          │──┐    │ id (PK)             │
│ email (unique)   │  │    │ user_id (FK)        │──┐
│ password_hash    │  │    │ user_query          │  │
│ display_name     │  │    │ selected_models     │  │
│ created_at       │  │    │ chairman_model      │  │
│ last_login       │  │    │ mode                │  │
│ lmarena_token    │  │    │ depth               │  │
└─────────────────┘  │    │ synthesis (text)    │  │
                     │    │ agreements (text)   │  │
                     │    │ divergences (text)  │  │
                     │    │ unique_insights     │  │
                     │    │ deliberation_log    │  │  (JSONB)
                     │    │ total_latency       │  │
                     │    │ created_at          │  │
                     └────┼─────────────────────┘  │
                          └────────────────────────┘
       ┌────────────────────────────────────────────┐
       │            model_responses                 │
       ├────────────────────────────────────────────┤
       │ id (PK)                                    │
       │ session_id (FK) ───────────────────────────┘
       │ model_name                                 │
       │ reasoning (text)   -- extracted from XML   │
       │ final_answer (text) -- full raw response   │
       │ confidence (float) -- self-reported        │
       │ latency (float)                            │
       │ status ('done','error','timeout')          │
       │ critique (text)   -- peer review           │
       │ critique_score (float)                     │
       │ raw_payload (JSONB) -- full LMArena output │
       └────────────────────────────────────────────┘
```

## Table Definitions (SQLAlchemy Models)

### Users
```python
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    lmarena_token = Column(String, nullable=True)  # optional per-user token
```

### Council Sessions
```python
class CouncilSession(Base):
    __tablename__ = "council_sessions"
    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=True)  # null if anonymous
    user_query = Column(Text, nullable=False)
    selected_models = Column(JSONB, nullable=False)  # ["claude","chatgpt"]
    chairman_model = Column(String, nullable=False)
    mode = Column(String, default="consensus")
    depth = Column(String, default="detailed")
    synthesis = Column(Text, nullable=True)  # unified answer
    agreements = Column(Text, nullable=True)
    divergences = Column(Text, nullable=True)
    unique_insights = Column(JSONB, nullable=True)
    deliberation_log = Column(JSONB, nullable=True)  # full timeline
    total_latency = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Model Responses
```python
class ModelResponse(Base):
    __tablename__ = "model_responses"
    id = Column(UUID, primary_key=True, default=uuid4)
    session_id = Column(UUID, ForeignKey("council_sessions.id"), nullable=False)
    model_name = Column(String, nullable=False)
    reasoning = Column(Text, nullable=True)   # extracted from <reasoning>
    final_answer = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True) # 0.0 - 1.0
    latency = Column(Float, nullable=False)
    status = Column(String, default="done")
    critique = Column(Text, nullable=True)
    critique_score = Column(Float, nullable=True)
    raw_payload = Column(JSONB, nullable=True) # for debugging
```

## Migrations

Using Alembic:

```bash
cd backend
alembic init migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

## Backup & Recovery

- Daily automated pg_dump via cron job.
- To restore: `pg_restore -d aicouncil backup.dump`

## Indexes for Performance

```sql
CREATE INDEX idx_sessions_user_id ON council_sessions(user_id);
CREATE INDEX idx_sessions_created ON council_sessions(created_at DESC);
CREATE INDEX idx_responses_session ON model_responses(session_id);
```

## Caching Strategy (Redis)

- Cache frequently asked queries with TTL = 1 hour.
- Cache model availability list – refresh every 10 minutes.
