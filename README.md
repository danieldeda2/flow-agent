# FlowAgent

**AI-powered orchestration across GitHub, Gmail, and Slack — in a single chat interface.**

FlowAgent connects your developer tools and lets you interact with all of them through natural language. Ask it to summarize your emails, check your GitHub issues, read your Slack channels, or do all three at once. It reasons across services, takes actions, and returns a unified response.

Live at [flow-agent.io](https://flow-agent.io)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, NextAuth.js |
| Backend | FastAPI, Python |
| Database | PostgreSQL (Railway) |
| Agent | LangGraph, LangChain, Claude Sonnet |
| Auth | OAuth 2.0 — GitHub, Google, Slack |
| Deploy | Vercel (frontend), Railway (backend + DB) |

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
│  /google/connect    → Custom Gmail OAuth flow   │
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

**Single Master Identity** — Users sign in with GitHub as their primary identity. Gmail and Slack are connected as additional services, all linked to the same master account. This prevents token confusion across providers.

**LangGraph Orchestrator** — A single stateful graph has tools for all three services. Claude decides which tools to call and in what order based on the user's natural language request. Tools fail gracefully when a service isn't connected.

**Separate OAuth Flows** — Gmail and Slack use custom FastAPI OAuth endpoints rather than NextAuth, giving full control over token scopes and storage.

---

## What FlowAgent Can Do

### GitHub
- List all your repositories
- Get open issues for any repo
- Create a new issue
- Close an issue
- Comment on an issue
- Get open pull requests
- View recent commit history

### Gmail
- Summarize unread emails
- Read the full body of any email
- Search emails by sender, subject, or keyword
- Mark emails as read
- Send an email
- Reply to an email

### Slack
- List all channels
- Read recent messages from any channel
- Send a message to a channel
- Reply to a thread
- Search messages by keyword across all channels
- Read direct messages

---

## Example Prompts

### Single Service

```
What are my unread emails?
```
```
Show me the open issues in my flow-agent repo
```
```
What channels do I have in Slack?
```
```
Show me the recent commits in my CarQuest repo
```
```
Search my emails for anything from GitHub
```

### Actions

```
Send an email to john@example.com with subject "Meeting" and body "Are you free Thursday?"
```
```
Create a GitHub issue in my flow-agent repo titled "Fix mobile layout" 
```
```
Send a message to #general saying "Deploying in 5 minutes"
```
```
Mark my most recent unread email as read
```
```
Close issue #12 in my portfolio repo
```

### Cross-Service Orchestration

```
Read my most recent email and create a GitHub issue about it in my flow-agent repo
```
```
Summarize my unread emails and open GitHub issues together
```
```
Check my Slack channels and emails and give me a full morning briefing
```
```
Search my emails for anything related to my CarQuest repo and summarize what you find
```
```
Send a Slack message to #dev with a summary of my open GitHub issues
```
```
Reply to my most recent email and then create a GitHub issue tracking the follow-up
```

---

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- PostgreSQL database
- GitHub OAuth App
- Google OAuth App (with Gmail API enabled)
- Slack App

### Environment Variables

**Frontend (`frontend/.env.local`)**
```
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_secret
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Backend (`backend/.env`)**
```
DATABASE_URL=your_postgres_url
ANTHROPIC_API_KEY=your_anthropic_key
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
SLACK_REDIRECT_URI=http://localhost:8000/slack/callback
GOOGLE_REDIRECT_URI=http://localhost:8000/google/callback
FRONTEND_URL=http://localhost:3000
```

### Running Locally

**Backend**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

### OAuth Setup

**GitHub** — Create an OAuth App at github.com/settings/developers
- Callback URL: `http://localhost:3000/api/auth/callback/github`

**Google** — Create credentials at console.cloud.google.com
- Enable the Gmail API
- Authorized redirect URIs: `http://localhost:8000/google/callback`

**Slack** — Create an app at api.slack.com
- Add the following bot token scopes: `channels:read`, `channels:history`, `groups:read`, `groups:history`, `im:read`, `im:history`, `mpim:read`, `mpim:history`, `users:read`, `users:read.email`, `team:read`, `chat:write`
- Redirect URL: `http://localhost:8000/slack/callback`

---

## Deployment

- **Frontend** — Vercel. Set root directory to `frontend` and add all environment variables.
- **Backend** — Railway. Set root directory to `backend` and add all environment variables. Start command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

---

## Author

Built by Daniel Deda — [GitHub](https://github.com/danieldeda)
