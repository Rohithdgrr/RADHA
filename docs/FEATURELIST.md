# 📋 Feature List

## ✅ Core Features (MVP)

### User Interface
- [x] Perplexity-style hero search bar.
- [x] Dark theme with cyan (#00BFFF) accents.
- [x] Model selector with toggles for 6+ models.
- [x] Unified answer with agree/diverge/unique insights sections.
- [x] Individual model response cards with full text.
- [x] Real-time streaming (token-by-token).
- [x] Latency display per model.

### Backend Orchestration
- [x] Parallel model execution (`asyncio.gather`).
- [x] Integration with LMArenaBridge (OpenAI-compatible API).
- [x] Prompt engineering for reasoning extraction (`<reasoning>` / `<answer>`).
- [x] Chairman synthesis with structured output (agreements, divergences, insights).
- [x] Server-Sent Events (SSE) for real-time updates.
- [x] Circuit breaker pattern (120-second timeout, retries).

### Database
- [x] PostgreSQL schema for users, conversations, and council sessions.
- [x] Full JSON storage of deliberation logs for replay.

### Authentication (simplified — Sept 2026)
- [x] **No website login** — anonymous sessions only, shareable via URL. Just log in at `arena.ai` to obtain `LMARENA_TOKEN`.
- [x] Secure storage of LMArena token in environment variables (server-side only, never exposed to frontend).
- [ ] Website auth (email/password, OAuth) removed — kept in git history for future private-deploy option.

## 🚀 Advanced Features (Phase 2)

- [ ] Council Modes: Consensus, Debate, Specialist, Weighted Voting.
- [ ] Peer review / critique generation.
- [ ] Analysis depth selector (Brief / Standard / Detailed).
- [ ] File uploads (images, PDFs) via LMArena's file bed server.
- [ ] PWA (Progressive Web App) support.
- [ ] Multi-language UI (i18n).
- [ ] Model performance analytics dashboard (admin view).

## 🔮 Future Features (Phase 3)

- [ ] Custom system prompt editor per model.
- [ ] Integration with RAG (Retrieval-Augmented Generation) via local vector DB.
- [ ] OpenAI-compatible API endpoint for third-party apps.
- [ ] Mobile app (React Native).
- [ ] Browser extension for quick queries.
- [ ] Community sharing of council sessions.
- [ ] Email/Slack alerts for token expiry.
