# Task Tracker API

A minimal learning-project skeleton for the Module 1 Task Tracker REST API, built with Python, FastAPI, and Pydantic. Persistence will use file-based JSON storage (per ADR), no database, no authentication, no Docker.

The API exposes CRUD endpoints for tasks and comments, plus search and filter combinations on `GET /tasks`. A single-file Kanban board frontend ([frontend/index.html](frontend/index.html)) talks to the API.

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

## Running the backend

With the virtual environment activated:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

## Opening the frontend

The backend must be running first (the board calls `http://localhost:8000`). Serve the
`frontend` folder on port 5500 — the origin the API's CORS config allows:

**Linux/macOS:**
```bash
python3 -m http.server 5500 --directory frontend
```

**Windows (PowerShell):**
```powershell
python -m http.server 5500 --directory frontend
```

Then open `http://localhost:5500/index.html` in your browser.

## Running the tests

Tests use `pytest`. Install it into the virtual environment if it isn't already:

```bash
pip install pytest
```

Run the full suite from the project root:

```bash
pytest
```

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
