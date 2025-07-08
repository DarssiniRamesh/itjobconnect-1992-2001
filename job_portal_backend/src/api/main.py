from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from .auth import auth_router
from .users import users_router
from .jobs import jobs_router

app = FastAPI(
    title="IT JobConnect API",
    description="Backend API server for job postings, user authentication, applicant profiles, employer data, and applications management.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}

# Register routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(jobs_router)
