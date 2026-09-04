# Data Model — AI Council Website (Phase 1)

> **Derived from:** `docs/DATABASE.md`, `research.md` U-03/U-06/U-07, `docs/BACKEND.md`
> **Stack:** PostgreSQL 15+, SQLAlchemy 2 (async), Alembic, Pydantic 2, UUIDv4, JSONB
> **Date:** 2026-09-04

## 1. Overview & ERD

```
users 1──∞ council_sessions 1──∞ model_responses
  │                │
  │                └─∞ deliberation_log (JSONB events, not a table)
  └─ (nullable FK enables anonymous sessions)
```

**Design decisions (from research):**
- **UUIDv4** PKs (distributed-safe, no enumeration). Decision: `pgcrypto` not needed, Python `uuid4()`.
- **JSONB** for `selected_models`, `unique_insights`, `deliberation_log`, `raw_payload` → GIN where queryable, else plain.
- **Soft nullable `user_id`** → anon sessions retained 7 days (Phase 2: GDPR purge job).
- **Async SQLAlchemy** (`AsyncSession`, `asyncpg` driver) to match `asyncio.gather` pipeline.
- **Timestamps UTC** (`datetime.utcnow` → `TIMESTAMPTZ` with `server_default=now()`).

---

## 2. Entity: User

**Table:** `users` | **Purpose:** Auth, token ownership, history scoping

| Field | Type (PG) | SQLAlchemy | Constraints | Validation (Pydantic) | Notes |
|-------|-----------|------------|-------------|-----------------------|-------|
| `id` | UUID PK | `UUID(as_uuid=True), primary_key=True, default=uuid4` | PK | — | Index implicit |
| `email` | VARCHAR(320) | `String(320), unique=True, nullable=False, index=True` | UNIQUE, NOT NULL, IE unique | `EmailStr`, `max_length=320`, lowercased on write | Login identifier |
| `password_hash` | VARCHAR(255) | `String(255), nullable=False` | NOT NULL | Never exposed, bcrypt 12 rounds | `passlib[bcrypt]` |
| `display_name` | VARCHAR(100) | `String(100), nullable=True` | — | `min_length=1 max_length=100` strip | Optional |
| `created_at` | TIMESTAMPTZ | `DateTime(timezone=True), server_default=func.now()` | NOT NULL | auto | |
| `last_login` | TIMESTAMPTZ | `DateTime(timezone=True), nullable=True` | — | auto on login | For analytics |
| `lmarena_token` | TEXT | `Text, nullable=True` | — | `min_length=100` if provided | Per-user override; null → global `LMARENA_TOKEN`. Encrypted at rest (Phase 3 vault) |
| `is_active` | BOOLEAN | `Boolean, default=True` | NOT NULL | — | Soft disable |

**Indexes:**
```sql
CREATE UNIQUE INDEX ux_users_email ON users (lower(email));
CREATE INDEX ix_users_created ON users (created_at DESC);
```

**State transitions:** `register → active → (login updates last_login) → deactivated (is_active=false)`

**Pydantic schemas:**
```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)

class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str | None
    created_at: datetime
    last_login: datetime | None
    model_config = ConfigDict(from_attributes=True)
```

---

## 3. Entity: CouncilSession

**Table:** `council_sessions` | **Purpose:** Single deliberation; owns synthesis + deliberation timeline

| Field | Type (PG) | SQLAlchemy | Constraints | Validation | Notes |
|-------|-----------|------------|-------------|------------|-------|
| `id` | UUID PK | `UUID(as_uuid=True), primary_key=True, default=uuid4` | PK | — | Shareable URL `/council/{id}` |
| `user_id` | UUID FK→users.id | `UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True` | FK, nullable | `UUID | None` | Null = anonymous |
| `user_query` | TEXT | `Text, nullable=False` | NOT NULL, CHECK length>0 | `min_length=1 max_length=10000` | Original prompt |
| `selected_models` | JSONB | `JSONB, nullable=False` | NOT NULL, CHECK jsonb_array_length>1 | `list[ModelId]` 2..8 items, unique | e.g. `["claude","chatgpt"]` |
| `chairman_model` | VARCHAR(50) | `String(50), nullable=False` | NOT NULL, CHECK in allowed list | `ModelId` must be in selected or fixed set | Default `claude` |
| `mode` | VARCHAR(20) | `String(20), default="consensus"` | CHECK in enum | `Literal["consensus","debate","specialist","weighted"]` | Phase 1: only `consensus` enforced, others 501 |
| `depth` | VARCHAR(20) | `String(20), default="detailed"` | CHECK in enum | `Literal["brief","standard","detailed"]` | Affects synthesis prompt length |
| `show_reasoning` | BOOLEAN | `Boolean, default=True` | NOT NULL | bool | Toggles `<reasoning>` extraction |
| `synthesis` | TEXT | `Text, nullable=True` | — | — | Chairman final answer; null while running |
| `agreements` | TEXT | `Text, nullable=True` | — | — | Parsed bulleted list or JSON |
| `divergences` | TEXT | `Text, nullable=True` | — | — | Parsed |
| `unique_insights` | JSONB | `JSONB, nullable=True` | — | `list[str] | None` | Per-model unique points |
| `deliberation_log` | JSONB | `JSONB, nullable=True` | — | `list[DeliberationEvent]` | Full SSE timeline for replay (see §5) |
| `total_latency` | DOUBLE PRECISION | `Float, nullable=True` | CHECK >=0 | `ge=0` | Wall time fan-out → fan-in end |
| `status` | VARCHAR(20) | `String(20), default="running"` | CHECK in enum | `Literal["running","done","error","partial"]` | `partial` if <2 models succeeded |
| `created_at` | TIMESTAMPTZ | `DateTime(timezone=True), server_default=func.now()` | NOT NULL, index | auto | History sort |
| `updated_at` | TIMESTAMPTZ | `DateTime(timezone=True), onupdate=func.now()` | — | auto | |

**ModelId enum (canonical):** `claude | chatgpt | gemini | deepseek | qwen | kimi | grok | llama` — mapped to LMArena internal IDs via `MODEL_MAPPINGS` YAML (see `API-CONFIG.md:24`).

**Indexes:**
```sql
CREATE INDEX ix_sessions_user_id ON council_sessions (user_id);
CREATE INDEX ix_sessions_created ON council_sessions (created_at DESC);
CREATE INDEX ix_sessions_status ON council_sessions (status);
CREATE INDEX ix_sessions_mode ON council_sessions (mode);
-- GIN for JSONB if we query by model:
CREATE INDEX ix_sessions_models_gin ON council_sessions USING GIN (selected_models);
```

**Lifecycle:**
```
running → done        (≥2 models succeeded, synthesis parsed)
running → partial     (1 model succeeded, synthesis with warning)
running → error       (<2 models, no synthesis)
running → (timeout) → partial/error (120s per model, total wall ~130s)
```

**Pydantic:**
```python
class CouncilSessionCreate(BaseModel):
    query: str = Field(min_length=1, max_length=10000)
    models: list[ModelId] = Field(min_length=2, max_length=8)
    mode: CouncilMode = "consensus"
    depth: Depth = "detailed"
    show_reasoning: bool = True
    chairman: ModelId = "claude"

    @field_validator("models")
    def unique_models(cls, v): 
        if len(set(v)) != len(v): raise ValueError("duplicate models")
        return v

class CouncilSessionRead(BaseModel):
    id: UUID
    user_id: UUID | None
    user_query: str
    selected_models: list[ModelId]
    chairman_model: ModelId
    mode: CouncilMode
    depth: Depth
    synthesis: str | None
    agreements: str | None
    divergences: str | None
    unique_insights: list[str] | None
    deliberation_log: list[DeliberationEvent] | None
    total_latency: float | None
    status: SessionStatus
    created_at: datetime
    updated_at: datetime | None
    responses: list[ModelResponseRead]  # joined
    model_config = ConfigDict(from_attributes=True)
```

---

## 4. Entity: ModelResponse

**Table:** `model_responses` | **Purpose:** One row per model per session; stores full trace for transparency & replay

| Field | Type (PG) | SQLAlchemy | Constraints | Validation | Notes |
|-------|-----------|------------|-------------|------------|-------|
| `id` | UUID PK | `UUID(as_uuid=True), primary_key=True, default=uuid4` | PK | — | |
| `session_id` | UUID FK→council_sessions.id | `UUID(as_uuid=True), ForeignKey("council_sessions.id", ondelete="CASCADE"), nullable=False, index=True` | FK CASCADE | UUID | Delete session → cascade |
| `model_name` | VARCHAR(50) | `String(50), nullable=False, index=True` | NOT NULL | `ModelId` | Denormalized for quick filter |
| `reasoning` | TEXT | `Text, nullable=True` | — | — | Extracted `<reasoning>` else null |
| `final_answer` | TEXT | `Text, nullable=False` | NOT NULL | `min_length=1` if status=done else "" | Full unabridged |
| `confidence` | DOUBLE PRECISION | `Float, nullable=True` | CHECK 0<=x<=1 | `ge=0 le=1` | Self-reported 0-100 normalized to 0-1; null if not parsed |
| `latency` | DOUBLE PRECISION | `Float, nullable=False` | NOT NULL, >=0 | `ge=0` | Seconds from request start to `model_done` |
| `token_count` | INTEGER | `Integer, nullable=True` | >=0 | `ge=0` | From bridge `usage` if provided |
| `status` | VARCHAR(20) | `String(20), default="done"` | CHECK in enum | `Literal["done","error","timeout"]` | |
| `error_message` | TEXT | `Text, nullable=True` | — | — | Only if status != done |
| `critique` | TEXT | `Text, nullable=True` | — | — | Debate mode: review of another model's answer |
| `critique_score` | DOUBLE PRECISION | `Float, nullable=True` | 0<=x<=10 | `ge=0 le=10` | Score out of 10 |
| `raw_payload` | JSONB | `JSONB, nullable=True` | — | dict | Full LMArena bridge output for debugging (redacted token) |
| `created_at` | TIMESTAMPTZ | `DateTime(timezone=True), server_default=func.now()` | NOT NULL | auto | |

**Indexes:**
```sql
CREATE INDEX ix_responses_session ON model_responses (session_id);
CREATE INDEX ix_responses_model ON model_responses (model_name);
CREATE INDEX ix_responses_status ON model_responses (status);
CREATE UNIQUE INDEX ux_responses_session_model ON model_responses (session_id, model_name);
```

**Unique constraint** prevents duplicate model per session (idempotent retry).

**Pydantic:**
```python
class ModelResponseRead(BaseModel):
    id: UUID
    session_id: UUID
    model_name: ModelId
    reasoning: str | None
    final_answer: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    latency: float = Field(ge=0)
    token_count: int | None = Field(default=None, ge=0)
    status: Literal["done","error","timeout"]
    error_message: str | None = None
    critique: str | None = None
    critique_score: float | None = Field(default=None, ge=0, le=10)
    raw_payload: dict | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

---

## 5. Deliberation Log (JSONB Event Timeline)

Stored in `council_sessions.deliberation_log` as ordered array for replay. Not a table (avoids join flood), but typed.

```typescript
type DeliberationEvent =
  | { type: "model_start"; model: ModelId; ts: string; session_id: string }
  | { type: "model_stream"; model: ModelId; delta: string; ts: string }  // optional persisted sampling
  | { type: "model_done"; model: ModelId; latency: number; status: string; ts: string }
  | { type: "critique_done"; reviewer: ModelId; reviewee: ModelId; score: number; ts: string }
  | { type: "synthesis_start"; chairman: ModelId; ts: string }
  | { type: "synthesis_stream"; delta: string; ts: string }
  | { type: "done"; total_latency: number; ts: string }
  | { type: "error"; model: ModelId; message: string; ts: string }
```

**Phase 1 choice:** Persist only `model_start/done` + `synthesis_start/done` + `error` (not every `model_stream` delta) to bound JSONB size. Full deltas are ephemeral SSE; final `final_answer` is source of truth.

---

## 6. Relationships & ORM Sketch

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    # ... as §2
    sessions: Mapped[list["CouncilSession"]] = relationship(back_populates="user", cascade="all, delete-orphan", lazy="selectin")

class CouncilSession(Base):
    __tablename__ = "council_sessions"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # ... as §3
    user: Mapped[User | None] = relationship(back_populates="sessions", lazy="joined")
    responses: Mapped[list["ModelResponse"]] = relationship(back_populates="session", cascade="all, delete-orphan", lazy="selectin", order_by="ModelResponse.model_name")

class ModelResponse(Base):
    __tablename__ = "model_responses"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("council_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    # ... as §4
    session: Mapped["CouncilSession"] = relationship(back_populates="responses", lazy="joined")
```

**Cascade:** Delete `CouncilSession` → delete its `ModelResponse`s. Delete `User` → set `council_sessions.user_id = NULL` (preserve anon history), not cascade sessions.

---

## 7. Validation Rules (Pydantic + DB)

| Rule | Enforced Where | Error |
|------|----------------|-------|
| `models` 2..8 unique, each in allow-list | Pydantic + DB CHECK jsonb_array_length | 422 Unprocessable |
| `chairman` must be in `models` or allow-list | Pydantic validator | 422 |
| `query` 1..10000 chars, stripped, not whitespace-only | Pydantic `field_validator` + DB CHECK | 422 |
| `mode`/`depth` enum | Pydantic Literal + DB CHECK | 422 |
| `confidence` 0-1 if present | Pydantic `ge/le` + DB CHECK | 422 |
| `email` valid, lowercased | `EmailStr` + DB `lower()` unique index | 409 Conflict if duplicate |
| `password` 8..128 | Pydantic | 422 |
| Anonymous allowed (`user_id null`) | DB nullable FK | — |
| <2 successful models → `status=error` 422 not 500 | App logic in `orchestrator.py` | 502 Bad Gateway with detail |
| `MAX_MODELS_PER_QUERY=8` env overrides | App config | 422 if exceeded |

---

## 8. Migrations (Alembic)

```bash
cd backend
alembic init migrations
# alembic.ini: sqlalchemy.url = postgresql+asyncpg://...
# env.py: target_metadata = Base.metadata, async engine
alembic revision --autogenerate -m "init users, council_sessions, model_responses"
alembic upgrade head

# Indexes added in same revision; GIN in separate if needed:
alembic revision -m "add gin index on selected_models"
```

**Downgrade** must drop indexes before tables.

---

## 9. Seed & Mock Data

```python
# backend/seed.py (dev only)
anon_session = CouncilSession(
    user_id=None,
    user_query="What is quantum computing?",
    selected_models=["claude","chatgpt","gemini"],
    chairman_model="claude",
    synthesis="Quantum computing uses qubits...",
    agreements="All agree on superposition",
    divergences="Gemini emphasizes error correction",
    unique_insights=["DeepSeek mentions photonic qubits"],
    status="done",
    total_latency=23.4,
    deliberation_log=[{"type":"model_start","model":"claude","ts":"..."}]
)
```

---

## 10. Open Questions Resolved vs Deferred

| Question | Resolution |
|----------|------------|
| Should `critique` be separate table? | **No** — column on `model_responses` suffices Phase 1 (1 critique per model max). Debate multi-round would need `critiques` table — Phase 2. |
| Store every SSE delta? | **No** — bounded log (start/done only). Full answers stored, deltas ephemeral. |
| `lmarena_token` encryption? | **Defer Phase 3** vault; store plaintext in dev, note `SECURITY.md`. |
| `confidence` extraction? | Best-effort regex `confidence:\s*(\d+)%` → normalize 0-1 else null. |
| Anonymous history pagination? | `GET /council/sessions?limit=20&offset=0&user_id=...` — anon sessions not listed unless `session_id` known (privacy). |

---

## 11. Review Checklist

- [x] 3 entities defined with fields, types, constraints, validation
- [x] Relationships, cascades, indexes specified
- [x] Pydantic schemas match DB CHECKs
- [x] Lifecycle/status enums documented
- [x] Alembic workflow
- [ ] **Pending review:** Approve before coding `orchestrator.py`
