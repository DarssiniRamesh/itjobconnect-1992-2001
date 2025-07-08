"""
jobs.py - Endpoints to manage jobs (CRUD for employers, search/view for all) and applications (apply, status for both sides).

Implements:
- Employers can post, edit, delete, and list their jobs
- Applicants can search, view, and apply to jobs
- Application submission, viewing, and status update
- Role-based access control for API endpoints
- Search filter and pagination support for job search
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

from .db import get_db
from .models import Job, Application
from .auth import get_current_user

jobs_router = APIRouter(prefix="/jobs", tags=["Jobs & Applications"])

# ===================== Pydantic Schemas ========================

class JobCreate(BaseModel):
    title: str = Field(..., description="Job title")
    description: str = Field(..., description="Job description")
    location: Optional[str] = Field(None, description="Job location")
    job_type: Optional[str] = Field(None, description="Full Time, Contract, Remote, etc.")
    keywords: Optional[str] = Field(None, description="Comma-separated keywords")

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    keywords: Optional[str] = None

class JobRead(BaseModel):
    id: int
    title: str
    description: str
    location: Optional[str]
    job_type: Optional[str]
    posted_at: datetime
    keywords: Optional[str]
    employer_id: int
    employer_name: Optional[str]

    class Config:
        orm_mode = True

class ApplicationCreate(BaseModel):
    cover_letter: Optional[str] = None

class ApplicationRead(BaseModel):
    id: int
    applicant_id: int
    applicant_name: Optional[str]
    job_id: int
    job_title: Optional[str]
    applied_at: datetime
    status: str
    cover_letter: Optional[str]

    class Config:
        orm_mode = True

class ApplicationStatusUpdate(BaseModel):
    # For employer: can set status
    status: Literal["submitted", "reviewed", "rejected", "accepted"]

# ========= JOB CRUD (Employer only: list, create, update, delete) ===========

# PUBLIC_INTERFACE
@jobs_router.post(
    "/",
    response_model=JobRead,
    summary="Post a new job (Employer only)",
    description="Employers can post a new job."
)
def create_job(job: JobCreate, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Employer can create a new job posting."""
    user, role = current
    if role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can post jobs")
    db_job = Job(
        title=job.title,
        description=job.description,
        location=job.location,
        job_type=job.job_type,
        keywords=job.keywords,
        employer_id=user.id
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    # Manually add employer_name for response
    return JobRead(
        id=db_job.id,
        title=db_job.title,
        description=db_job.description,
        location=db_job.location,
        job_type=db_job.job_type,
        posted_at=db_job.posted_at,
        keywords=db_job.keywords,
        employer_id=db_job.employer_id,
        employer_name=user.company_name
    )

# PUBLIC_INTERFACE
@jobs_router.put(
    "/{job_id}",
    response_model=JobRead,
    summary="Edit a job (Employer only)",
    description="Edit own job posting. Employer must own the job."
)
def update_job(job_id: int, update: JobUpdate, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Employer can update their own job."""
    user, role = current
    if role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can update jobs")
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if not db_job or db_job.employer_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found or not your job post")
    for field, value in update.dict(exclude_unset=True).items():
        setattr(db_job, field, value)
    db.commit()
    db.refresh(db_job)
    return JobRead(
        id=db_job.id,
        title=db_job.title,
        description=db_job.description,
        location=db_job.location,
        job_type=db_job.job_type,
        posted_at=db_job.posted_at,
        keywords=db_job.keywords,
        employer_id=db_job.employer_id,
        employer_name=user.company_name
    )

# PUBLIC_INTERFACE
@jobs_router.delete(
    "/{job_id}",
    summary="Delete a job posting (Employer only)",
    description="Employers can delete their own job posting. This will also remove all related applications."
)
def delete_job(job_id: int, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Employer deletes their job and its applications."""
    user, role = current
    if role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can delete jobs")
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if not db_job or db_job.employer_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found or not yours")
    db.delete(db_job)
    db.commit()
    return {"detail": "Job deleted"}

# PUBLIC_INTERFACE
@jobs_router.get(
    "/me",
    response_model=List[JobRead],
    summary="List my jobs (Employer)",
    description="Employers: List jobs posted by self."
)
def list_my_jobs(skip: int = 0, limit: int = 20, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Employers list their own jobs."""
    user, role = current
    if role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can list their jobs")
    jobs = db.query(Job).filter(Job.employer_id == user.id).offset(skip).limit(limit).all()
    return [
        JobRead(
            id=j.id,
            title=j.title,
            description=j.description,
            location=j.location,
            job_type=j.job_type,
            posted_at=j.posted_at,
            keywords=j.keywords,
            employer_id=j.employer_id,
            employer_name=user.company_name
        )
        for j in jobs
    ]

# =============== Job listing/search for ALL users =====================

# PUBLIC_INTERFACE
@jobs_router.get(
    "/",
    response_model=List[JobRead],
    summary="Search and list jobs",
    description="Any user can view/search job postings. Supports keyword/location/type filter and pagination."
)
def list_jobs(
    q: Optional[str] = Query(None, alias="query", description="Search text in title/desc/keywords"),
    location: Optional[str] = Query(None, description="Filter by location"),
    job_type: Optional[str] = Query(None, description="Filter by job_type"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """View/search jobs, filterable and paginated."""
    query = db.query(Job)
    if q:
        ilike_query = f"%{q.lower()}%"
        query = query.filter(
            or_(
                Job.title.ilike(ilike_query),
                Job.description.ilike(ilike_query),
                Job.keywords.ilike(ilike_query)
            )
        )
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if job_type:
        query = query.filter(Job.job_type.ilike(f"%{job_type}%"))
    jobs = query.order_by(Job.posted_at.desc()).offset(skip).limit(limit).all()
    # Get employer info for each job
    def _get_emp_name(j):
        if hasattr(j, 'employer') and j.employer:
            return j.employer.company_name
        return None
    return [
        JobRead(
            id=j.id,
            title=j.title,
            description=j.description,
            location=j.location,
            job_type=j.job_type,
            posted_at=j.posted_at,
            keywords=j.keywords,
            employer_id=j.employer_id,
            employer_name=_get_emp_name(j)
        )
        for j in jobs
    ]

# PUBLIC_INTERFACE
@jobs_router.get(
    "/{job_id}",
    response_model=JobRead,
    summary="Get single job by ID",
    description="View details of a job posting"
)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get job details by ID."""
    job = db.query(Job).options(joinedload(Job.employer)).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead(
        id=job.id,
        title=job.title,
        description=job.description,
        location=job.location,
        job_type=job.job_type,
        posted_at=job.posted_at,
        keywords=job.keywords,
        employer_id=job.employer_id,
        employer_name=job.employer.company_name if job.employer else None
    )

# ============================ APPLICATIONS ===============================

# PUBLIC_INTERFACE
@jobs_router.post(
    "/{job_id}/apply",
    response_model=ApplicationRead,
    summary="Apply to a job (Applicant only)",
    description="Applicant can apply to a job (prevents duplicate applications)."
)
def apply_to_job(
    job_id: int,
    application: ApplicationCreate,
    db: Session = Depends(get_db),
    current=Depends(get_current_user)
):
    """Applicant submits an application to a job, cannot apply twice."""
    user, role = current
    if role != "applicant":
        raise HTTPException(status_code=403, detail="Only applicants can apply")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = db.query(Application).filter(
        Application.applicant_id == user.id, Application.job_id == job_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already applied to this job")
    app = Application(
        applicant_id=user.id,
        job_id=job_id,
        cover_letter=application.cover_letter,
        status="submitted"
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return ApplicationRead(
        id=app.id,
        applicant_id=app.applicant_id,
        applicant_name=user.name,
        job_id=app.job_id,
        job_title=job.title,
        applied_at=app.applied_at,
        status=app.status,
        cover_letter=app.cover_letter
    )

# PUBLIC_INTERFACE
@jobs_router.get(
    "/applications/me",
    response_model=List[ApplicationRead],
    summary="List my job applications (Applicant)",
    description="Applicant: View all your applications and statuses"
)
def list_my_applications(db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Applicant sees all their job applications."""
    user, role = current
    if role != "applicant":
        raise HTTPException(status_code=403, detail="Only applicants can view this")
    apps = db.query(Application).options(joinedload(Application.job)).filter(
        Application.applicant_id == user.id
    ).order_by(Application.applied_at.desc()).all()
    return [
        ApplicationRead(
            id=a.id,
            applicant_id=a.applicant_id,
            applicant_name=user.name,
            job_id=a.job_id,
            job_title=a.job.title if a.job else None,
            applied_at=a.applied_at,
            status=a.status,
            cover_letter=a.cover_letter
        )
        for a in apps
    ]

# PUBLIC_INTERFACE
@jobs_router.get(
    "/{job_id}/applications",
    response_model=List[ApplicationRead],
    summary="List applications for a job (Employer)",
    description="Employer: View all applications for your job posting"
)
def list_applications_for_job(job_id: int, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Employer lists applications for their posted job."""
    user, role = current
    if role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can view applications for their jobs")
    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not your job")
    apps = db.query(Application).options(joinedload(Application.applicant)).filter(
        Application.job_id == job_id
    ).order_by(Application.applied_at.desc()).all()
    return [
        ApplicationRead(
            id=a.id,
            applicant_id=a.applicant_id,
            applicant_name=a.applicant.name if a.applicant else None,
            job_id=a.job_id,
            job_title=job.title,
            applied_at=a.applied_at,
            status=a.status,
            cover_letter=a.cover_letter
        )
        for a in apps
    ]

# PUBLIC_INTERFACE
@jobs_router.put(
    "/applications/{application_id}/status",
    response_model=ApplicationRead,
    summary="Update application status (Employer only)",
    description="Employer updates an application's status (submitted, reviewed, rejected, accepted)."
)
def update_application_status(application_id: int, data: ApplicationStatusUpdate, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Employer can update status for application to their job."""
    user, role = current
    if role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can update status")
    app = db.query(Application).join(Job).filter(
        Application.id == application_id, Job.employer_id == user.id
    ).options(joinedload(Application.applicant), joinedload(Application.job)).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or not for your job")
    app.status = data.status
    db.commit()
    db.refresh(app)
    return ApplicationRead(
        id=app.id,
        applicant_id=app.applicant_id,
        applicant_name=app.applicant.name if app.applicant else None,
        job_id=app.job_id,
        job_title=app.job.title if app.job else None,
        applied_at=app.applied_at,
        status=app.status,
        cover_letter=app.cover_letter
    )

# PUBLIC_INTERFACE
@jobs_router.get(
    "/applications/job/{job_id}/me",
    response_model=ApplicationRead,
    summary="View my application to specific job (Applicant)",
    description="Applicants: get your application (if any) for a specific job"
)
def get_my_application_for_job(job_id: int, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Get applicant's application for a given job."""
    user, role = current
    if role != "applicant":
        raise HTTPException(status_code=403, detail="Only applicants can view application")
    app = db.query(Application).filter(
        Application.job_id == job_id, Application.applicant_id == user.id
    ).options(joinedload(Application.job)).first()
    if not app:
        raise HTTPException(status_code=404, detail="No application found")
    return ApplicationRead(
        id=app.id,
        applicant_id=app.applicant_id,
        applicant_name=user.name,
        job_id=app.job_id,
        job_title=app.job.title if app.job else None,
        applied_at=app.applied_at,
        status=app.status,
        cover_letter=app.cover_letter
    )
