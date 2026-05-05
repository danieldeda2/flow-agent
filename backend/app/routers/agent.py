from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProviderToken
from app.agents.github_agent import run_agent as run_github_agent
from app.agents.gmail_agent import run_gmail_agent
from app.agents.slack_agent import run_slack_agent
from app.agents.orchestrator import run_orchestrator
from pydantic import BaseModel

router = APIRouter()

class AgentRequest(BaseModel):
    email: str
    message: str
    provider: str = "github"

class OrchestratorRequest(BaseModel):
    github_email: str
    gmail_email: str
    slack_email: str
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
    def get_token(email: str, provider: str):
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User not found: {email}")
        token = db.query(ProviderToken).filter(
            ProviderToken.user_id == user.id,
            ProviderToken.provider == provider
        ).first()
        if not token:
            raise HTTPException(status_code=404, detail=f"{provider} token not found for {email}")
        return token

    github_token = get_token(request.github_email, "github")
    gmail_token = get_token(request.gmail_email, "google")
    slack_token = get_token(request.slack_email, "slack")

    response = run_orchestrator(
        github_token=github_token.access_token,
        gmail_token=gmail_token.access_token,
        gmail_refresh_token=gmail_token.refresh_token,
        slack_token=slack_token.access_token,
        message=request.message
    )

    return {"response": response}