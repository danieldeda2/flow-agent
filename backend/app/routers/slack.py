from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProviderToken
import requests
import os

router = APIRouter()

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
SLACK_REDIRECT_URI = "http://localhost:8000/slack/callback"
SLACK_SCOPES = "channels:read,groups:read,im:read,im:history,users:read"

@router.get("/slack/connect")
def slack_connect():
    url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={SLACK_CLIENT_ID}"
        f"&user_scope={SLACK_SCOPES}"
        f"&redirect_uri={SLACK_REDIRECT_URI}"
    )
    return RedirectResponse(url)

@router.get("/slack/callback")
def slack_callback(code: str, db: Session = Depends(get_db)):
    response = requests.post("https://slack.com/api/oauth.v2.access", data={
        "client_id": SLACK_CLIENT_ID,
        "client_secret": SLACK_CLIENT_SECRET,
        "code": code,
        "redirect_uri": SLACK_REDIRECT_URI,
    })

    data = response.json()
    if not data.get("ok"):
        return {"error": data.get("error")}

    user_token = data["authed_user"]["access_token"]
    slack_user_id = data["authed_user"]["id"]

    user_info = requests.get(
        "https://slack.com/api/users.info",
        headers={"Authorization": f"Bearer {user_token}"},
        params={"user": slack_user_id}
    ).json()

    slack_user = user_info.get("user", {})
    profile = slack_user.get("profile", {})
    email = profile.get("email") or f"{slack_user_id}@slack.local"
    name = slack_user.get("real_name", slack_user_id)
    avatar = profile.get("image_48", "")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=name, avatar_url=avatar)
        db.add(user)
        db.flush()

    token = db.query(ProviderToken).filter(
        ProviderToken.user_id == user.id,
        ProviderToken.provider == "slack"
    ).first()

    if token:
        token.access_token = user_token
    else:
        token = ProviderToken(
            user_id=user.id,
            provider="slack",
            access_token=user_token
        )
        db.add(token)

    db.commit()
    return RedirectResponse("http://localhost:3000?slack=connected")