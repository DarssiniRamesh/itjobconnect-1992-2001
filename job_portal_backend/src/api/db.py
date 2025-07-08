from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from .models import Base

# Database URL from environment variable or default (job_portal_database container provides SQLITE_DB)
raw_db_val = os.environ.get("SQLITE_DB", "sqlite:///./job_portal.db")
# If the string is not a valid SQLAlchemy URL (no scheme), prepend sqlite:/// (or sqlite://// for absolute path)
if "://" not in raw_db_val:
    # Absolute path check
    if raw_db_val.startswith("/"):
        DATABASE_URL = f"sqlite:///{raw_db_val}"
    else:
        DATABASE_URL = f"sqlite:///{raw_db_val}"
else:
    DATABASE_URL = raw_db_val

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

# PUBLIC_INTERFACE
def get_db():
    """Dependency that provides a SQLAlchemy session for each FastAPI request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
