from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProviderToken, ConnectedAccount
import requests
import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = "http://localhost:8000/google/callback"
GOOGLE_SCOPES = " ".join([
    "openid",
    "email",
    "profile",
    "https://mail.google.com/",
])

@router.get("/google/connect")
def google_connect(master_email: str):
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={requests.utils.quote(GOOGLE_SCOPES)}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={master_email}"
    )
    return RedirectResponse(url)

@router.get("/google/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    master_user = db.query(User).filter(User.email == state).first()
    if not master_user:
        return {"error": f"Master user not found: {state}"}

    # Exchange code for tokens
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).json()

    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")

    if not access_token:
        return {"error": "Failed to get access token", "details": token_response}

    # Get user info
    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    email = user_info.get("email")
    name = user_info.get("name", "")
    avatar = user_info.get("picture", "")

    if not email:
        return {"error": "Could not get Google email"}

    # Upsert Google user record
    google_user = db.query(User).filter(User.email == email).first()
    if not google_user:
        google_user = User(email=email, name=name, avatar_url=avatar)
        db.add(google_user)
        db.flush()

    # Store token under Google user
    token = db.query(ProviderToken).filter(
        ProviderToken.user_id == google_user.id,
        ProviderToken.provider == "google"
    ).first()

    if token:
        token.access_token = access_token
        token.refresh_token = refresh_token
    else:
        token = ProviderToken(
            user_id=google_user.id,
            provider="google",
            access_token=access_token,
            refresh_token=refresh_token
        )
        db.add(token)

    # Link ConnectedAccount to master user
    connected = db.query(ConnectedAccount).filter(
        ConnectedAccount.master_user_id == master_user.id,
        ConnectedAccount.provider == "google"
    ).first()

    if connected:
        connected.provider_email = email
    else:
        connected = ConnectedAccount(
            master_user_id=master_user.id,
            provider="google",
            provider_email=email
        )
        db.add(connected)

    db.commit()
    return RedirectResponse(f"{os.getenv('FRONTEND_URL')}?google=connected")
