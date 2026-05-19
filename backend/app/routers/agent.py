from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProviderToken
from app.agents.github_agent import run_agent as run_github_agent
from app.agents.gmail_agent import run_gmail_agent
from app.agents.slack_agent import run_slack_agent
from app.agents.orchestrator import run_orchestrator
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class AgentRequest(BaseModel):
    email: str
    message: str
    provider: str = "github"

class OrchestratorRequest(BaseModel):
    github_email: Optional[str] = None
    gmail_email: Optional[str] = None
    slack_email: Optional[str] = None
    message: str

@router.post("/agent/run")
def run_agent_endpoint(request: AgentRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = db.query(ProviderToken).filter(
        ProviderToken.user_id == user.id,
        ProviderToken.provider == request.provider
    ).first()
    if not token:
        raise HTTPException(status_code=404, detail=f"{request.provider} token not found")

    if request.provider == "github":
        response = run_github_agent(token.access_token, request.message)
    elif request.provider == "google":
        response = run_gmail_agent(token.access_token, token.refresh_token, request.message)
    elif request.provider == "slack":
        response = run_slack_agent(token.access_token, request.message)
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    return {"response": response}

@router.post("/agent/orchestrate")
def run_orchestrator_endpoint(request: OrchestratorRequest, db: Session = Depends(get_db)):
    def get_token(email: Optional[str], provider: str):
        if not email:
            return None
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        token = db.query(ProviderToken).filter(
            ProviderToken.user_id == user.id,
            ProviderToken.provider == provider
        ).first()
        return token

    github_token = get_token(request.github_email, "github")
    gmail_token = get_token(request.gmail_email, "google")
    slack_token = get_token(request.slack_email, "slack")

    if not any([github_token, gmail_token, slack_token]):
        raise HTTPException(status_code=400, detail="No services connected")

    # Callback that fires the moment Gmail refreshes a token — writes it to DB immediately
    def on_gmail_refresh(new_token: str):
        try:
            gmail_token.access_token = new_token
            db.commit()
        except Exception as e:
            print(f"Failed to persist refreshed Gmail token: {e}")

    response = run_orchestrator(
        github_token=github_token.access_token if github_token else None,
        gmail_token=gmail_token.access_token if gmail_token else None,
        gmail_refresh_token=gmail_token.refresh_token if gmail_token else None,
        slack_token=slack_token.access_token if slack_token else None,
        message=request.message,
        on_gmail_refresh=on_gmail_refresh if gmail_token else None,
    )

    return {"response": response}