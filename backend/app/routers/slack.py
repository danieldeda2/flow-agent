from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProviderToken, ConnectedAccount
import requests
import os

router = APIRouter()

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI", "http://localhost:8000/slack/callback")
SLACK_SCOPES = "channels:read,channels:history,groups:read,groups:history,im:read,im:history,mpim:read,mpim:history,users:read,users:read.email,team:read,chat:write"

@router.get("/slack/connect")
def slack_connect(master_email: str):
    url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={SLACK_CLIENT_ID}"
        f"&scope={SLACK_SCOPES}"
        f"&redirect_uri={SLACK_REDIRECT_URI}"
        f"&state={master_email}"
    )
    return RedirectResponse(url)

@router.get("/slack/callback")
def slack_callback(code: str, state: str, db: Session = Depends(get_db)):
    master_user = db.query(User).filter(User.email == state).first()
    if not master_user:
        return {"error": f"Master user not found: {state}"}

    response = requests.post("https://slack.com/api/oauth.v2.access", data={
        "client_id": SLACK_CLIENT_ID,
        "client_secret": SLACK_CLIENT_SECRET,
        "code": code,
        "redirect_uri": SLACK_REDIRECT_URI,
    })

    data = response.json()
    if not data.get("ok"):
        return {"error": data.get("error")}

    bot_token = data["access_token"]
    authed_user_id = data["authed_user"]["id"]

    # Use bot token to look up the human user's profile
    user_info = requests.get(
        "https://slack.com/api/users.info",
        headers={"Authorization": f"Bearer {bot_token}"},
        params={"user": authed_user_id}
    ).json()

    slack_user = user_info.get("user", {})
    profile = slack_user.get("profile", {})
    email = profile.get("email") or f"{data['team']['id']}@slack.local"
    name = slack_user.get("real_name", authed_user_id)
    avatar = profile.get("image_48", "")

    # Upsert the Slack user record
    slack_user_record = db.query(User).filter(User.email == email).first()
    if not slack_user_record:
        slack_user_record = User(email=email, name=name, avatar_url=avatar)
        db.add(slack_user_record)
        db.flush()

    # Store the bot token under the Slack user
    token = db.query(ProviderToken).filter(
        ProviderToken.user_id == slack_user_record.id,
        ProviderToken.provider == "slack"
    ).first()

    if token:
        token.access_token = bot_token
    else:
        token = ProviderToken(
            user_id=slack_user_record.id,
            provider="slack",
            access_token=bot_token
        )
        db.add(token)

    # Link ConnectedAccount to the MASTER user (the one logged into FlowAgent)
    connected = db.query(ConnectedAccount).filter(
        ConnectedAccount.master_user_id == master_user.id,
        ConnectedAccount.provider == "slack"
    ).first()

    if connected:
        connected.provider_email = email
    else:
        connected = ConnectedAccount(
            master_user_id=master_user.id,
            provider="slack",
            provider_email=email
        )
        db.add(connected)

    db.commit()
    
    frontend_url = os.getenv('FRONTEND_URL')
    print(f"FRONTEND_URL: {frontend_url}")
    return RedirectResponse(f"{frontend_url}?slack=connected")