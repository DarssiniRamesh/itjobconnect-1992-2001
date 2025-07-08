"""
users.py - User-related endpoints for the job portal.

Includes endpoints for administrative functions and listing/filtering users (excluding sensitive info).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .db import get_db
from .models import Applicant, Employer

users_router = APIRouter(prefix="/users", tags=["Users"])

# PUBLIC_INTERFACE
@users_router.get(
    "/applicants",
    summary="List all applicants",
    description="Lists all applicant user profiles.",
)
def list_applicants(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    applicants = db.query(Applicant).offset(skip).limit(limit).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "summary": u.summary,
            "skills": u.skills,
            "experience": u.experience,
            "created_at": u.created_at,
            "is_active": u.is_active,
        }
        for u in applicants
    ]

@users_router.get(
    "/employers",
    summary="List all employers",
    description="Lists all employer user profiles.",
)
def list_employers(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    employers = db.query(Employer).offset(skip).limit(limit).all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "email": e.email,
            "company_name": e.company_name,
            "company_website": e.company_website,
            "created_at": e.created_at,
            "is_active": e.is_active,
        }
        for e in employers
    ]
