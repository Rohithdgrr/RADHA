# 🛠️ Setup & Installation Guide

## Prerequisites

- **Docker** and **Docker Compose** (recommended) OR Node.js 18+ / Python 3.10+.
- A valid LMArena.ai account (free).
- Git.

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourname/ai-council.git
cd ai-council
```

## Step 2: Obtain LMArena Authentication Token

1.  Open your regular Chrome/Firefox browser.
2.  Navigate to `https://arena.ai` and log in.
3.  Press `F12` to open Developer Tools.
4.  Go to the **Application** tab (Chrome) or **Storage** tab (Firefox).
5.  Expand **Cookies** and click on `https://arena.ai`.
6.  Find the cookie named **`arena-auth-prod-v1`**.
7.  Copy its full value (a long base64-encoded string).

## Step 3: Configure Environment Variables

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# LMArenaBridge
LMARENA_TOKEN=your_copied_token_here
LMARENA_BRIDGE_URL=http://lmarenabridge:8000

# Database
DATABASE_URL=postgresql://admin:password@postgres:5432/aicouncil

# Backend
BACKEND_PORT=8000
FRONTEND_PORT=3000
SECRET_KEY=your_strong_secret_key
ADMIN_PASSWORD=your_admin_password
```

## Step 4: Run with Docker Compose (Recommended)

```bash
docker-compose up -d --build
```

This will spin up:
- **PostgreSQL** on port 5432.
- **LMArenaBridge** on port 8001.
- **FastAPI Backend** on port 8000.
- **Next.js Frontend** on port 3000.

Wait for all containers to be healthy (approx. 30 seconds). Then open `http://localhost:3000`.

## Step 5: Verify Setup

1.  Open `http://localhost:8000/health` – should return `{"status":"ok"}`.
2.  Try a simple query: `http://localhost:8000/models` – should return a list of available models from LMArena.

## Manual Setup (Without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### LMArenaBridge
Follow the [LMArenaBridge documentation](https://github.com/lmarenabridge/lmarenabridge) to run it locally.

## Troubleshooting Setup

| Problem | Solution |
| :--- | :--- |
| `Error: Connection refused` | Ensure LMArenaBridge is running and the URL in `.env` is correct. |
| `401 Unauthorized` | Your LMArena token has expired. Re-copy a fresh token and restart containers. |
| `PostgreSQL connection failed` | Wait 10 seconds after `docker-compose up` – the DB needs time to initialize. |
