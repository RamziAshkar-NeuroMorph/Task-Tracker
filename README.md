# Task Tracker API

A minimal learning-project skeleton for the Module 1 Task Tracker REST API, built with Python, FastAPI, and Pydantic. Persistence will use file-based JSON storage (per ADR), no database, no authentication, no Docker.

This skeleton currently exposes only a single `/health` endpoint. CRUD functionality for tasks will be added in a later module.

## Requirements

- Python 3.9+
- pip

## Setup

1. Clone or download this project, then navigate into it:
```bash
   cd task-tracker-api
```

2. Create and activate a virtual environment:

   **Linux/macOS:**
```bash
   python3 -m venv venv
   source venv/bin/activate
```

   **Windows (PowerShell):**
```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
```

3. Install dependencies:
```bash
   pip install -r requirements.txt
```

4. Copy the example environment file and adjust if needed:

   **Linux/macOS:**
```bash
   cp .env.example .env
```

   **Windows (PowerShell):**
```powershell
   Copy-Item .env.example .env
```

## Running the server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

## Testing the health endpoint

```bash
curl http://localhost:8000/health
```

Expected response shape:
```json
{
  "status": "ok",
  "timestamp": "2026-06-30T12:00:00.000000+00:00"
}
```

## API Documentation (Swagger UI)

Once the server is running, open your browser to:

```
http://localhost:8000/docs
```
