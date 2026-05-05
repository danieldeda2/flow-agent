from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProviderToken
import requests

router = APIRouter()

@router.get("/github/repos/{email}")
def get_user_repos(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = db.query(ProviderToken).filter(
        ProviderToken.user_id == user.id,
        ProviderToken.provider == "github"
    ).first()
    if not token:
        raise HTTPException(status_code=404, detail="GitHub token not found")

    response = requests.get(
        "https://api.github.com/user/repos",
        headers={
            "Authorization": f"Bearer {token.access_token}",
            "Accept": "application/vnd.github+json"
        }
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="GitHub API error")

    repos = [{"name": r["name"], "url": r["html_url"], "private": r["private"]} for r in response.json()]
    return {"repos": repos}