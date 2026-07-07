from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(
    title="Task Tracker API",
    description="Module 1 Task Tracker REST API skeleton (file-based JSON storage).",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict:
    """Basic liveness check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
