from datetime import datetime, timezone
from typing import Annotated
from app.business_rules import validate_status_transition
from app.models import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    TaskCreate,
    TaskFilters,
    TaskResponse,
    TaskUpdate,
)
from app import storage
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Task Tracker API",
    description="Module 1 Task Tracker REST API skeleton (file-based JSON storage).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5173",
        "null",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict:
    """Basic liveness check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["tasks"])
def create_task(payload: TaskCreate) -> TaskResponse:
    return storage.add_task(payload)


@app.get("/tasks", response_model=list[TaskResponse], tags=["tasks"])
def list_tasks(filters: Annotated[TaskFilters, Query()]) -> list[TaskResponse]:
    return storage.get_all_tasks(
        status=filters.status,
        priority=filters.priority,
        search=filters.search,
        assignee=filters.assignee,
    )


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def get_task(task_id: str) -> TaskResponse:
    task = storage.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return task


@app.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def update_task(task_id: str, payload: TaskUpdate) -> TaskResponse:
    if payload.status is not None:
        existing = storage.get_task_by_id(task_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
        validate_status_transition(existing.status, payload.status)

    task = storage.update_task(task_id, payload)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
def delete_task(task_id: str) -> None:
    if not storage.delete_task(task_id):
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")


def _ensure_task_exists(task_id: str) -> None:
    if storage.get_task_by_id(task_id) is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")


@app.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["comments"],
)
def create_comment(task_id: str, payload: CommentCreate) -> CommentResponse:
    _ensure_task_exists(task_id)
    return storage.add_comment(task_id, payload)


@app.get("/tasks/{task_id}/comments", response_model=list[CommentResponse], tags=["comments"])
def list_comments(task_id: str) -> list[CommentResponse]:
    _ensure_task_exists(task_id)
    return storage.get_comments(task_id)


@app.patch(
    "/tasks/{task_id}/comments/{comment_id}",
    response_model=CommentResponse,
    tags=["comments"],
)
def update_comment(task_id: str, comment_id: str, payload: CommentUpdate) -> CommentResponse:
    _ensure_task_exists(task_id)
    comment = storage.update_comment(task_id, comment_id, payload)
    if comment is None:
        raise HTTPException(
            status_code=404, detail=f"Comment with id {comment_id} not found"
        )
    return comment


@app.delete(
    "/tasks/{task_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["comments"],
)
def delete_comment(task_id: str, comment_id: str) -> None:
    _ensure_task_exists(task_id)
    if not storage.delete_comment(task_id, comment_id):
        raise HTTPException(
            status_code=404, detail=f"Comment with id {comment_id} not found"
        )
