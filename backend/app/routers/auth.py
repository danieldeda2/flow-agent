from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProviderToken
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class GithubCallbackRequest(BaseModel):
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    access_token: str

@router.post("/auth/github/callback")
def github_callback(data: GithubCallbackRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user:
        user = User(
            email=data.email,
            name=data.name,
            avatar_url=data.avatar_url
        )
        db.add(user)
        db.flush()

    token = db.query(ProviderToken).filter(
        ProviderToken.user_id == user.id,
        ProviderToken.provider == "github"
    ).first()

    if token:
        token.access_token = data.access_token
    else:
        token = ProviderToken(
            user_id=user.id,
            provider="github",
            access_token=data.access_token
        )
        db.add(token)

    db.commit()
    return {"status": "ok"}