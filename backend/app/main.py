from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.database import engine, Base
from app.models import User, ProviderToken
from app.routers.auth import router as auth_router
from app.routers.github import router as github_router
from app.routers.agent import router as agent_router

load_dotenv()

app = FastAPI(title="FlowAgent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(github_router)
app.include_router(agent_router)

@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database connected and tables created")
    except Exception as e:
        print(f"❌ Database error: {e}")

@app.get("/health")
def health_check():
    return {"status": "ok"}