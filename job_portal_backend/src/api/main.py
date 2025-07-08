from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Import models and Base for table creation
from .models import Base

# Database URL from environment variable or default (job_portal_database container provides SQLITE_DB)
DATABASE_URL = os.environ.get("SQLITE_DB", "sqlite:///./job_portal.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PUBLIC_INTERFACE
def get_db():
    """Dependency that provides a SQLAlchemy session for each FastAPI request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"message": "Healthy"}
