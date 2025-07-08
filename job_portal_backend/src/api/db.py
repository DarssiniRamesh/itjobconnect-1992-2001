from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from .models import Base

# Database URL from environment variable or default (job_portal_database container provides SQLITE_DB)
import sys

raw_db_val = os.environ.get("SQLITE_DB", "sqlite:///./job_portal.db")
DATABASE_URL = None

# If the string is not a valid SQLAlchemy URL (no scheme), prepend sqlite:/// (or sqlite://// for absolute path)
if "://" not in raw_db_val:
    # Absolute path check
    if raw_db_val.startswith("/"):
        candidate_path = raw_db_val
        db_uri = f"sqlite:///{candidate_path}"
    else:
        candidate_path = os.path.join(os.getcwd(), raw_db_val)
        db_uri = f"sqlite:///{candidate_path}"
else:
    db_uri = raw_db_val
    # Infer candidate_path for check (if possible)
    if db_uri.startswith("sqlite:///"):
        candidate_path = db_uri.replace("sqlite:///", "", 1)
    else:
        candidate_path = None

# Verify DB file exists or is writable, fallback if not
fallback_db_uri = "sqlite:///./job_portal.db"
if candidate_path:
    try:
        # File accessibility check
        if os.path.exists(candidate_path):
            DATABASE_URL = db_uri
        else:
            # Try to create it if the parent is writable
            parent_dir = os.path.dirname(candidate_path)
            if os.access(parent_dir, os.W_OK):
                open(candidate_path, "a").close()
                DATABASE_URL = db_uri
            else:
                print(f"[db.py] WARNING: DB file {candidate_path} not accessible, falling back to local ./job_portal.db", file=sys.stderr)
                DATABASE_URL = fallback_db_uri
    except Exception as e:
        print(f"[db.py] ERROR accessing DB file {candidate_path}: {e}. Falling back to ./job_portal.db", file=sys.stderr)
        DATABASE_URL = fallback_db_uri
else:
    DATABASE_URL = db_uri

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

try:
    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)
    # Test connection
    with engine.connect():
        print(f"[db.py] Successfully connected to DB: {DATABASE_URL}", file=sys.stderr)
except Exception as e:
    print(f"[db.py] ERROR: Unable to initialize/connect to DB at {DATABASE_URL}: {e}", file=sys.stderr)
    print("[db.py] Failing FastAPI startup; check DB path and permissions.", file=sys.stderr)
    raise

# PUBLIC_INTERFACE
def get_db():
    """Dependency that provides a SQLAlchemy session for each FastAPI request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
