"""
auth.py - User authentication and role-based login endpoints for the job portal.

Handles:
- Registration (Employer/Applicant)
- Login (JWT token issuance)
- Profile viewing/updating (authenticated)
- Role support (applicant, employer)
- Secure password hashing and validation.

Uses OAuth2 password bearer and JWT authentication for security.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, constr, Field
from typing import Optional, Literal
from datetime import datetime, timedelta
import os
import jwt
from passlib.context import CryptContext

from .db import get_db
from .models import Applicant, Employer

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretjwtkey!change_this!")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserType(str):
    APPLICANT = "applicant"
    EMPLOYER = "employer"

# Pydantic Schemas

class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Type of the token (bearer)")

class TokenData(BaseModel):
    email: EmailStr
    role: Literal["applicant", "employer"]

class ApplicantRegister(BaseModel):
    name: str
    email: EmailStr
    password: constr(min_length=8)
    summary: Optional[str] = None
    skills: Optional[str] = None
    experience: Optional[str] = None

class EmployerRegister(BaseModel):
    name: str
    email: EmailStr
    password: constr(min_length=8)
    company_name: Optional[str] = None
    company_website: Optional[str] = None

class ApplicantProfile(BaseModel):
    id: int
    name: str
    email: EmailStr
    summary: Optional[str]
    skills: Optional[str]
    experience: Optional[str]
    created_at: datetime
    is_active: bool

    class Config:
        orm_mode = True

class EmployerProfile(BaseModel):
    id: int
    name: str
    email: EmailStr
    company_name: Optional[str]
    company_website: Optional[str]
    created_at: datetime
    is_active: bool

    class Config:
        orm_mode = True

# Utils

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return TokenData(email=email, role=role)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Public: get current user (applicant or employer)
# PUBLIC_INTERFACE
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Returns the current user (applicant/employer+role) from JWT token."""
    token_data = decode_access_token(token)
    if token_data.role == UserType.APPLICANT:
        user = db.query(Applicant).filter(Applicant.email == token_data.email).first()
    elif token_data.role == UserType.EMPLOYER:
        user = db.query(Employer).filter(Employer.email == token_data.email).first()
    else:
        user = None
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user, token_data.role

# Registration endpoints
@auth_router.post(
    "/register/applicant",
    response_model=Token,
    summary="Register as job-seeker (applicant)",
    description="Create a new applicant account and returns a JWT token."
)
def register_applicant(reg: ApplicantRegister, db: Session = Depends(get_db)):
    if db.query(Applicant).filter(Applicant.email == reg.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    applicant = Applicant(
        name=reg.name,
        email=reg.email,
        hashed_password=get_password_hash(reg.password),
        summary=reg.summary,
        skills=reg.skills,
        experience=reg.experience,
    )
    db.add(applicant)
    db.commit()
    db.refresh(applicant)
    token = create_access_token(data={"sub": reg.email, "role": "applicant"})
    return Token(access_token=token, token_type="bearer")

@auth_router.post(
    "/register/employer",
    response_model=Token,
    summary="Register as employer",
    description="Create a new employer account and returns a JWT token."
)
def register_employer(reg: EmployerRegister, db: Session = Depends(get_db)):
    if db.query(Employer).filter(Employer.email == reg.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    employer = Employer(
        name=reg.name,
        email=reg.email,
        hashed_password=get_password_hash(reg.password),
        company_name=reg.company_name,
        company_website=reg.company_website,
    )
    db.add(employer)
    db.commit()
    db.refresh(employer)
    token = create_access_token(data={"sub": reg.email, "role": "employer"})
    return Token(access_token=token, token_type="bearer")

# Login: OAuth2 password-bearer
@auth_router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and receive JWT access token",
    description="Logs in as employer or applicant and returns a JWT for API use.",
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Try both applicant and employer if not specified
    user, detected_role = None, None
    applicant = db.query(Applicant).filter(Applicant.email == form_data.username).first()
    employer = db.query(Employer).filter(Employer.email == form_data.username).first()
    if applicant and verify_password(form_data.password, applicant.hashed_password):
        user, detected_role = applicant, "applicant"
    elif employer and verify_password(form_data.password, employer.hashed_password):
        user, detected_role = employer, "employer"
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user.email, "role": detected_role})
    return Token(access_token=token, token_type="bearer")

# Profile view/update
@auth_router.get(
    "/me",
    response_model=ApplicantProfile | EmployerProfile,
    summary="Get current user profile",
    description="Return current user's (applicant or employer) profile and details."
)
def get_profile(current=Depends(get_current_user)):
    user, role = current
    if role == "applicant":
        return ApplicantProfile.from_orm(user)
    else:
        return EmployerProfile.from_orm(user)

@auth_router.put(
    "/me",
    response_model=ApplicantProfile | EmployerProfile,
    summary="Update own profile",
    description="Update your applicant or employer profile details."
)
def update_profile(
    summary: Optional[str] = Body(None),
    skills: Optional[str] = Body(None),
    experience: Optional[str] = Body(None),
    company_name: Optional[str] = Body(None),
    company_website: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    user, role = current
    updated = False
    if role == "applicant":
        if summary is not None:
            user.summary = summary
            updated = True
        if skills is not None:
            user.skills = skills
            updated = True
        if experience is not None:
            user.experience = experience
            updated = True
    elif role == "employer":
        if company_name is not None:
            user.company_name = company_name
            updated = True
        if company_website is not None:
            user.company_website = company_website
            updated = True
    if not updated:
        raise HTTPException(status_code=400, detail="No fields to update")
    db.commit()
    db.refresh(user)
    # Return updated profile model
    if role == "applicant":
        return ApplicantProfile.from_orm(user)
    else:
        return EmployerProfile.from_orm(user)
