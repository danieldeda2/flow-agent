from fastapi import FastAPI
from dotenv import load_dotenv
from app.database import engine, Base
from app.models import User

load_dotenv()

app = FastAPI(title="FlowAgent API")

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