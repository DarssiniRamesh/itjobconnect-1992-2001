# IT JobConnect API Documentation

This document describes the API endpoints provided by the IT JobConnect FastAPI backend. Each endpoint includes its method, route, summary, required/requested parameters, authentication, expected request/response schema, and potential errors.

**Base URL:** 
- When running locally: `http://localhost:3001`
- Deployed: as configured

**Authentication:**  
Some endpoints require authentication using a JWT Bearer token. Register or log in to obtain the token, then set the HTTP header:  
`Authorization: Bearer <access_token>`

---

## 1. Health Check

- **GET /**  
  - **Summary:** Application health check
  - **Auth:** None
  - **Response:**  
    ```
    {
      "message": "Healthy"
    }
    ```
---

## 2. Authentication Endpoints (`/auth`)

### Register as Applicant

- **POST /auth/register/applicant**
  - **Summary:** Register a job-seeking applicant and receive JWT token
  - **Request Body:**
    ```json
    {
      "name": "John Doe",
      "email": "john@example.com",
      "password": "at_least_8_chars",
      "summary": "Experienced IT professional", // Optional
      "skills": "Python,Cloud,DevOps",         // Optional
      "experience": "5 years in backend dev"   // Optional
    }
    ```
  - **Responses:**  
    - `200 OK`: 
      ```
      {
        "access_token": "<JWT token>",
        "token_type": "bearer"
      }
      ```
    - `409 Conflict`: Email already registered

---

### Register as Employer

- **POST /auth/register/employer**
  - **Summary:** Register an employer and receive JWT token
  - **Request Body:**
    ```json
    {
      "name": "Jane Smith",
      "email": "jane@company.com",
      "password": "at_least_8_chars",
      "company_name": "TechCorp",      // Optional
      "company_website": "https://..." // Optional
    }
    ```
  - **Responses:** Same as applicant registration (with JWT token).

---

### Login (Applicant/Employer)

- **POST /auth/login**
  - **Summary:** Authenticate and obtain JWT
  - **Form Data:** (Use `application/x-www-form-urlencoded`)
    - `username` — email
    - `password`
  - **Responses:**
    - `200 OK`: JWT token (as above)
    - `401 Unauthorized`: Invalid credentials

---

### Get Current User Profile

- **GET /auth/me**
  - **Auth:** Required (JWT Bearer)
  - **Response:**  
    Applicant:
    ```json
    {
      "id": 1,
      "name": "John",
      "email": "john@example.com",
      "summary": "...",
      "skills": "...",
      "experience": "...",
      "created_at": "...",
      "is_active": true
    }
    ```
    Employer:  
    ```json
    {
      "id": 2,
      "name": "Jane",
      "email": "jane@company.com",
      "company_name": "TechCorp",
      "company_website": "https://...",
      "created_at": "...",
      "is_active": true
    }
    ```
  - **Errors:** `401 Unauthorized` (invalid/missing token)

---

### Update Own Profile

- **PUT /auth/me**
  - **Auth:** Required (JWT Bearer)
  - **Request Body:**  
    *(Fields are optional; provide those to update)*
    - Applicants: `summary`, `skills`, `experience`
    - Employers: `company_name`, `company_website`
  - **Response:** Updated user profile (same schema as above)
  - **Errors:**  
    - `400 Bad Request`: No updatable fields provided  
    - `401 Unauthorized`: Not logged in

---

## 3. User Listing Endpoints (`/users`)

### List Applicants

- **GET /users/applicants?skip=0&limit=20**
  - **Summary:** List all applicants (paginated)
  - **Auth:** None
  - **Query Params:**  
    - `skip` (int): Offset for pagination (default 0)
    - `limit` (int): Max results (default 20)
  - **Response:**
    ```json
    [
      {
        "id": 1,
        "name": "John",
        "email": "john@example.com",
        "summary": "...",
        "skills": "...",
        "experience": "...",
        "created_at": "...",
        "is_active": true
      },
      ...
    ]
    ```

### List Employers

- **GET /users/employers?skip=0&limit=20**
  - **Summary:** List all employer profiles (paginated)
  - **Auth:** None
  - **Query Params:**  
    - `skip`, `limit`
  - **Response:**
    ```json
    [
      {
        "id": 2,
        "name": "Jane",
        "email": "jane@company.com",
        "company_name": "TechCorp",
        "company_website": "https://...",
        "created_at": "...",
        "is_active": true
      },
      ...
    ]
    ```

---

## 4. Job & Application Endpoints (`/jobs`)

### Create Job Posting (Employer)

- **POST /jobs/**
  - **Auth:** Employer (JWT Bearer)
  - **Request Body:**
    ```json
    {
      "title": "Backend Engineer",
      "description": "Work on cloud...",
      "location": "Remote",
      "job_type": "Full Time",        // Optional
      "keywords": "Python,Cloud"      // Optional
    }
    ```
  - **Response:** (Job object)
  - **Errors:**  
    - `403 Forbidden`: Only employers can post jobs

---

### Update Existing Job (Employer Owns)

- **PUT /jobs/{job_id}**
  - **Auth:** Employer (JWT)
  - **Request Body:** *(Any subset of)*
    ```json
    {
      "title": "Updated title",
      "description": "...",
      "location": "Remote",
      "job_type": "Contract",
      "keywords": "Python,DB"
    }
    ```
  - **Response:** Updated job object
  - **Errors:**  
    - `403 Forbidden`: Only employers  
    - `404 Not Found`: Job not found or not your post

---

### Delete Job Posting (Employer Owns)

- **DELETE /jobs/{job_id}**
  - **Auth:** Employer (JWT)
  - **Response:**
    ```json
    { "detail": "Job deleted" }
    ```
  - **Errors:**  
    - `403 Forbidden`, `404 Not Found`

---

### List My Jobs (Employer)

- **GET /jobs/me?skip=0&limit=20**
  - **Auth:** Employer only
  - **Response:** List of jobs posted by employer (see schema from create job)
  - **Errors:** `403 Forbidden`

---

### Search & List All Jobs

- **GET /jobs/?query=python&location=Berlin&job_type=Remote&skip=0&limit=20**
  - **Auth:** None (open to all)
  - **Query Params:**
    - `query` (search by title/desc/keywords, case-insensitive)
    - `location` (filter)
    - `job_type` (filter)
    - `skip`, `limit` (pagination)
  - **Response:** List of jobs (see above)

---

### Get Single Job By ID

- **GET /jobs/{job_id}**
  - **Auth:** None
  - **Response:** Job object (see above)
  - **Errors:** `404 Not Found`

---

### Apply to a Job (Applicant)

- **POST /jobs/{job_id}/apply**
  - **Auth:** Applicant (JWT)
  - **Request Body:**
    ```json
    { "cover_letter": "Optional pitch" }
    ```
  - **Response:** Application object  
    ```json
    {
      "id": 1,
      "applicant_id": 1,
      "applicant_name": "Alice",
      "job_id": 5,
      "job_title": "Backend Engineer",
      "applied_at": "...",
      "status": "submitted",
      "cover_letter": "I am very interested in..."
    }
    ```
  - **Errors:**  
    - `403 Forbidden`: Only applicants  
    - `404 Not Found`: Job not found  
    - `409 Conflict`: Already applied

---

### List My Job Applications (Applicant)

- **GET /jobs/applications/me**
  - **Auth:** Applicant (JWT)
  - **Response:** List of application objects (see above)

---

### List Applications for a Job (Employer)

- **GET /jobs/{job_id}/applications**
  - **Auth:** Employer (JWT)
  - **Response:** List of applications (see above)
  - **Errors:**  
    - `403 Forbidden`, `404 Not Found`

---

### Update Application Status (Employer)

- **PUT /jobs/applications/{application_id}/status**
  - **Auth:** Employer (JWT)
  - **Request Body:**
    ```json
    { "status": "reviewed" } // Allowed: submitted, reviewed, rejected, accepted
    ```
  - **Response:** Updated application object
  - **Errors:** `403 Forbidden`, `404 Not Found`

---

### Get My Application for a Job (Applicant)

- **GET /jobs/applications/job/{job_id}/me**
  - **Auth:** Applicant (JWT)
  - **Response:** Application object for this job (if any)
  - **Errors:**  
    - `403 Forbidden`, `404 Not Found`

---

## 5. Error Response Format

Errors are returned using error HTTP codes (`400`, `401`, `403`, `404`, `409`), with a body:

```json
{ "detail": "Error message" }
```

---

## 6. Authentication & Security

- **JWT Bearer Token:**  
  Register or log in to receive a JWT. Provide as `Authorization: Bearer <token>` on endpoints requiring authentication.
- **Applicant vs. Employer Roles:**  
  Most operations are limited appropriately by user type (e.g., only applicants can apply to jobs; only employers can post jobs).
- **Password Hashing:**  
  All passwords are securely hashed in the database.

---

## 7. OpenAPI/Swagger

Interactive documentation and the full OpenAPI schema are available at:

- Swagger UI: `/docs`  
- ReDoc: `/redoc`  

Example:  
https://vscode-internal-8-beta.beta01.cloud.kavia.ai:3001/docs

---

## 8. API Endpoint Overview (Mermaid Diagram)

```mermaid
graph TD
    HEALTH[GET /]:::public
    REG_APPL[POST /auth/register/applicant]:::public
    REG_EMPL[POST /auth/register/employer]:::public
    LOGIN[POST /auth/login]:::public
    ME[GET /auth/me]:::private
    ME_UPD[PUT /auth/me]:::private
    APPLISTS[GET /users/applicants]:::public
    EMPLISTS[GET /users/employers]:::public
    JOBS[GET /jobs/]:::public
    JOBID[GET /jobs/{job_id}]:::public
    JOB_C[POST /jobs/]:::employer
    JOB_U[PUT /jobs/{job_id}]:::employer
    JOB_D[DELETE /jobs/{job_id}]:::employer
    JOB_ME[GET /jobs/me]:::employer
    JOB_APPLY[POST /jobs/{job_id}/apply]:::applicant
    MYAPPS[GET /jobs/applications/me]:::applicant
    JOBAPP[GET /jobs/{job_id}/applications]:::employer
    APPSTAT[PUT /jobs/applications/{application_id}/status]:::employer
    MYJOBAPP[GET /jobs/applications/job/{job_id}/me]:::applicant

    classDef public fill:#dfeddc,stroke:#273043;
    classDef employer fill:#e8eefa,stroke:#2D9CDB;
    classDef applicant fill:#f8e8d9,stroke:#27AE60;
    classDef private fill:#f5f5f5,stroke:#999;
```

---

## 9. Additional Notes

- **Pagination:** List endpoints accept `skip` and `limit` query parameters for pagination.
- **Filtering & Search:** Jobs can be searched by query, location, and job_type.
- **Relationships:** Applications link applicants and jobs, jobs link to employers.
- **Data Integrity:** Employer/applicant ownership enforced on all endpoints.

---

## 10. References

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Project Swagger UI](/docs)
- Database schema: see `src/api/models.py`
- Authentication scheme: JWT, see `src/api/auth.py`

---

_Last updated: 2024-06_

