from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProviderToken
from app.agents.github_agent import run_agent
from pydantic import BaseModel

router = APIRouter()

class AgentRequest(BaseModel):
    email: str
    message: str

@router.post("/agent/run")
def run_agent_endpoint(request: AgentRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = db.query(ProviderToken).filter(
        ProviderToken.user_id == user.id,
        ProviderToken.provider == "github"
    ).first()
    if not token:
        raise HTTPException(status_code=404, detail="GitHub token not found")

    response = run_agent(token.access_token, request.message)
    return {"response": response}