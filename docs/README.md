# 🤖 AI Council – Perplexity-Style Multi-Model Deliberation

**AI Council** is a free, open-source web application that runs your query across 6+ leading AI models (ChatGPT, Claude, Gemini, DeepSeek, Qwen, **Kimi K2.5 / K3**) simultaneously, synthesizes a unified answer, and displays full individual responses – all without API keys, using headless browser automation via LMArenaBridge.

> **Models (Sept 2026 latest):** `claude-sonnet-4 (20250514)`, `gpt-5 (20250806)`, `gemini-2.5-pro`, `deepseek-v3.1`, `qwen3-72b`, `kimi-k2.5` (default) / `kimi-k3` (preview, 256k). See `API-CONFIG.md` for full version map.

## ✨ Key Features

- **Perplexity-Style UI** – Clean, dark-themed, hero search bar, unified answer, model cards.
- **Parallel Model Execution** – Query all selected models concurrently via LMArenaBridge.
- **Full Transparency** – View the complete reasoning, final answer, and confidence scores for each model.
- **Chairman Synthesis** – A designated model reads all responses and produces a consensus answer, highlighting agreements, divergences, and unique insights.
- **Council Modes** – Consensus (default), Debate, Specialist, and Weighted Voting.
- **Real-Time Streaming** – Live token-by-token streaming via Server-Sent Events.
- **Session Persistence** – Full conversation history stored in PostgreSQL.
- **Completely Free** – No API keys, no credit card required (uses LMArena web interface).

## 🛠️ Tech Stack

- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Backend**: FastAPI (Python) + WebSockets
- **AI Gateway**: LMArenaBridge (OpenAI-compatible bridge to 400+ models)
- **Database**: PostgreSQL (Neon / Supabase / Local)
- **Deployment**: Docker Compose or Vercel + AWS

## 🚀 Quick Start (no website account needed)

```bash
git clone https://github.com/yourname/ai-council.git
cd ai-council
cp .env.example .env
# Add your LMArena authentication token to .env (login at https://arena.ai → F12 → Cookies → arena-auth-prod-v1)
docker-compose up -d
# or without Docker (sqlite):
pip install -r backend/requirements.txt && python -m alembic -c backend/alembic.ini upgrade head
npm --prefix frontend install && npm --prefix frontend run dev
```

Open `http://localhost:3000` and start querying. **No sign-up required** — just log in at `arena.ai` once to get the token.

## 📚 Documentation

- **[WORKING.md](./WORKING.md)** – How the council orchestration works
- **[SETUP.md](./SETUP.md)** – Detailed installation and configuration
- **[UIUX.md](./UIUX.md)** – Design philosophy and user flows
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** – System architecture diagram and data flow
- **[USAGE.md](./USAGE.md)** – Usage guide
- **[FEATURELIST.md](./FEATURELIST.md)** – Feature breakdown
- **[PHASEWISEPLAN.md](./PHASEWISEPLAN.md)** – Development roadmap
- **[TECH-STACK.md](./TECH-STACK.md)** – Technology stack details
- **[FUTURE-SCOPE.md](./FUTURE-SCOPE.md)** – Vision beyond MVP
- **[PROCESS.md](./PROCESS.md)** – Development workflow
- **[BACKEND.md](./BACKEND.md)** – Backend architecture
- **[API-CONFIG.md](./API-CONFIG.md)** – API configuration
- **[DATABASE.md](./DATABASE.md)** – Database schema
- **[ENV.md](./ENV.md)** – Environment variables
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** – Deployment guide
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** – Contributing guidelines

## 📄 License

MIT – Free for personal and commercial use.

## ⚠️ Disclaimer

This project automates access to LMArena.ai and other web interfaces. Use responsibly and respect the Terms of Service of all platforms involved.
