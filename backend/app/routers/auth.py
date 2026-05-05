from fastapi import APIRouter, Depends, HTTPException, Request
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
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    print("AUTH CALLBACK DATA:", data)
    
    email = data.get("email")
    if not email:
        print("NO EMAIL FOUND IN:", data)
        return {"status": "error", "detail": "no email"}

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            name=data.get("name"),
            avatar_url=data.get("avatar_url")
        )
        db.add(user)
        db.flush()

    token = db.query(ProviderToken).filter(
        ProviderToken.user_id == user.id,
        ProviderToken.provider == data.get("provider")
    ).first()

    if token:
        token.access_token = data.get("access_token")
        token.refresh_token = data.get("refresh_token")
    else:
        token = ProviderToken(
            user_id=user.id,
            provider=data.get("provider"),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token")
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