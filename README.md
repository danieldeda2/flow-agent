# FlowAgent

An AI-powered orchestration platform that connects GitHub, Gmail, and Slack into a single conversational interface. Ask natural language questions across all three services simultaneously — FlowAgent reasons across them and takes real actions on your behalf.

![FlowAgent](https://img.shields.io/badge/Built%20with-Claude%20Sonnet-4f8eff?style=flat-square) ![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square) ![Next.js](https://img.shields.io/badge/Frontend-Next.js-000000?style=flat-square) ![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791?style=flat-square)

---

## What it does

FlowAgent lets you interact with your connected services through a single chat interface powered by Claude. It can read across services and take actions:

```
"Give me a full briefing — summarize my unread emails, open GitHub issues, and Slack activity"

"Read my most recent email and create a GitHub issue about it in my CarQuest repo"

"What repos do I have on GitHub and do any of my recent emails relate to them?"
```

Every command runs through a LangGraph agent that decides which services to call, executes the right API calls with your stored tokens, and synthesizes the results into a single coherent response.

---

## Tech Stack

| Layer - Technology |

| Frontend - Next.js 16, TypeScript, NextAuth.js |
| Backend - FastAPI, Python |
| Database - PostgreSQL (Railway) |
| Agents - LangGraph, LangChain, Claude Sonnet |
| Auth - OAuth 2.0 — GitHub, Google, Slack |
| Deployment - Vercel (frontend), Railway (backend + DB)

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Next.js Frontend               │
│         NextAuth.js · OAuth Sign-in UI          │
└──────────────────────┬──────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────┐
│                  FastAPI Backend                │
│                                                 │
│  /auth/callback     → Save OAuth tokens to DB   │
│  /auth/connected    → Resolve provider emails   │
│  /agent/orchestrate → Run cross-service agent   │
│  /slack/connect     → Custom Slack OAuth flow   │
└──────────┬───────────────────────┬──────────────┘
           │                       │
┌──────────▼──────────┐  ┌────────▼──────────────┐
│  PostgreSQL (DB)    │  │   LangGraph Agent     │
│                     │  │                       │
│  users              │  │   github tools        │
│  provider_tokens    │  │   gmail tools         │
│  connected_accounts │  │   slack tools         │
└─────────────────────┘  └───────────────────────┘
```

### Key Design Decisions

**Connected Accounts System** — A user who signs in with GitHub and connects Gmail and Slack has their tokens linked under one master identity. The orchestrator resolves the right token for each provider automatically.

**LangGraph Orchestrator** — Rather than routing requests to individual service agents, a single stateful graph has tools for all three services. Claude decides which tools to call and in what order based on the user's natural language request.

**Custom Slack OAuth** — NextAuth's built-in Slack provider doesn't support user-scoped tokens cleanly. FlowAgent implements a custom OAuth flow directly in FastAPI for full control over scopes and token extraction.

---

## Features

- **Multi-provider OAuth** — GitHub, Gmail, and Slack with refresh token support
- **Cross-service reasoning** — Single agent with tools spanning all three services
- **Real write actions** — Create GitHub issues, with more write operations extensible
- **Multi-tenant** — Each user's tokens are isolated in PostgreSQL
- **Token refresh** — Gmail access tokens refresh automatically on expiry
- **Clean UI** — Dark, minimal chat interface showing connection status per service

---

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL (or Railway account)
- Anthropic API key
- GitHub, Google, and Slack OAuth apps

### Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SLACK_CLIENT_ID=...
SLACK_CLIENT_SECRET=...
```

```bash
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
NEXTAUTH_SECRET=...
NEXTAUTH_URL=http://localhost:3000
```

```bash
npm run dev
```

### OAuth App Configuration

**GitHub** — Homepage URL: `http://localhost:3000` · Callback: `http://localhost:3000/api/auth/callback/github`

**Google** — Redirect URI: `http://localhost:3000/api/auth/callback/google` · Scopes: `openid email profile gmail.readonly`

**Slack** — Redirect URL: `http://localhost:8000/slack/callback` · User Token Scopes: `channels:read channels:history groups:read groups:history im:read im:history users:read`

---

## Project Structure

```
flowagent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, startup
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models/              # User, ProviderToken, ConnectedAccount
│   │   ├── routers/
│   │   │   ├── auth.py          # OAuth callbacks, token retrieval
│   │   │   ├── agent.py         # Agent + orchestrator endpoints
│   │   │   ├── github.py        # GitHub API endpoints
│   │   │   └── slack.py         # Custom Slack OAuth flow
│   │   └── agents/
│   │       ├── github_agent.py  # GitHub LangGraph agent
│   │       ├── gmail_agent.py   # Gmail LangGraph agent
│   │       ├── slack_agent.py   # Slack LangGraph agent
│   │       └── orchestrator.py  # Cross-service agent
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Main chat interface
│   │   ├── layout.tsx           # SessionProvider wrapper
│   │   ├── globals.css          # Design tokens
│   │   ├── components/
│   │   │   ├── Sidebar.tsx      # Connection status + user info
│   │   │   ├── ChatWindow.tsx   # Message history
│   │   │   └── MessageInput.tsx # Input bar
│   │   └── api/auth/            # NextAuth route handler
│   └── package.json
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/callback` | Save OAuth token on sign-in |
| GET | `/auth/token/{email}/{provider}` | Retrieve provider token |
| GET | `/auth/connected/{email}` | Get all connected provider emails |
| POST | `/agent/run` | Run single-service agent |
| POST | `/agent/orchestrate` | Run cross-service orchestrator |
| GET | `/slack/connect` | Initiate Slack OAuth flow |
| GET | `/slack/callback` | Handle Slack OAuth callback |
| GET | `/health` | Health check |

---

## Extending FlowAgent

Adding a new tool to the orchestrator takes about 10 lines:

```python
@tool
def create_github_pr(repo_name: str, title: str, body: str) -> str:
    """Create a pull request in a GitHub repository"""
    response = requests.post(
        f"https://api.github.com/repos/{username}/{repo_name}/pulls",
        headers={"Authorization": f"Bearer {github_token}"},
        json={"title": title, "body": body, "head": "main", "base": "main"}
    )
    return f"PR created: {response.json()['html_url']}"
```

Add it to `make_orchestrator_tools` and the agent will automatically know when to use it.
