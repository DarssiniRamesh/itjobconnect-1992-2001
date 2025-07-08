# models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# Association table for many-to-many relationship: Job <-> Applicant (Applications)
class Application(Base):
    """
    Table linking Applicants to Jobs (application submissions).
    """
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    applicant_id = Column(Integer, ForeignKey("applicants.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    applied_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(32), default="submitted")  # e.g., submitted, reviewed, rejected, accepted
    # Optional: cover letter or additional information
    cover_letter = Column(Text, nullable=True)

    # Relationships
    applicant = relationship("Applicant", back_populates="applications")
    job = relationship("Job", back_populates="applications")

class Employer(Base):
    """
    IT employer organization/user able to post jobs.
    """
    __tablename__ = "employers"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(128), nullable=False, index=True)
    email = Column(String(128), nullable=False, unique=True, index=True)
    hashed_password = Column(String(128), nullable=False)
    company_name = Column(String(128), nullable=True)
    company_website = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    # Relationships
    jobs = relationship("Job", back_populates="employer", cascade="all, delete-orphan")

class Applicant(Base):
    """
    Job-seeking user with a profile and applications.
    """
    __tablename__ = "applicants"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(128), nullable=False, index=True)
    email = Column(String(128), nullable=False, unique=True, index=True)
    hashed_password = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    # Profile fields
    summary = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)  # Comma-separated for simplicity
    experience = Column(Text, nullable=True)  # Text blob or serialized JSON for richer experience

    # Relationships
    applications = relationship("Application", back_populates="applicant", cascade="all, delete-orphan")

class Job(Base):
    """
    Job posting details.
    """
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(128), nullable=False, index=True)
    description = Column(Text, nullable=False)
    location = Column(String(128), nullable=True)
    job_type = Column(String(64), nullable=True) # e.g.: Full Time, Contract, Remote
    posted_at = Column(DateTime, default=datetime.utcnow)
    employer_id = Column(Integer, ForeignKey("employers.id", ondelete="CASCADE"), nullable=False, index=True)

    # Optional: desired skills as keywords
    keywords = Column(Text, nullable=True)

    # Relationships
    employer = relationship("Employer", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")

# ## Utility
# To create all tables, import Base and call Base.metadata.create_all(engine) after engine is created.

