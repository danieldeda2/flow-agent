from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProviderToken
from app.agents.github_agent import run_agent as run_github_agent
from app.agents.gmail_agent import run_gmail_agent
from pydantic import BaseModel

router = APIRouter()

class AgentRequest(BaseModel):
    email: str
    message: str
    provider: str = "github"

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
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    return {"response": response}