from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProviderToken
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class CallbackRequest(BaseModel):
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    access_token: str
    refresh_token: Optional[str]
    provider: str

@router.post("/auth/callback")
def auth_callback(data: CallbackRequest, db: Session = Depends(get_db)):
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
        ProviderToken.provider == data.provider
    ).first()

    if token:
        token.access_token = data.access_token
        token.refresh_token = data.refresh_token
    else:
        token = ProviderToken(
            user_id=user.id,
            provider=data.provider,
            access_token=data.access_token,
            refresh_token=data.refresh_token
        )
        db.add(token)

    db.commit()
    return {"status": "ok"}

@router.get("/auth/token/{email}/{provider}")
def get_token(email: str, provider: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = db.query(ProviderToken).filter(
        ProviderToken.user_id == user.id,
        ProviderToken.provider == provider
    ).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    return {
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
        "provider": token.provider
    }