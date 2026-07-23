from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.models import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)

_tasks: dict[str, TaskResponse] = {}
_comments: dict[str, list[CommentResponse]] = {}


def add_task(payload: TaskCreate) -> TaskResponse:
    now = datetime.now(timezone.utc)
    task = TaskResponse(
        id=str(uuid4()),
        title=payload.title,
        description=payload.description or "",
        status=payload.status,
        priority=payload.priority,
        assignee=payload.assignee,
        created_at=now,
        updated_at=now,
    )
    _tasks[task.id] = task
    return task


def get_all_tasks(status=None, priority=None, search=None, assignee=None) -> list[TaskResponse]:
    tasks = list(_tasks.values())
    if status is not None:
        tasks = [task for task in tasks if task.status == status]
    if priority is not None:
        tasks = [task for task in tasks if task.priority == priority]
    if assignee is not None:
        tasks = [task for task in tasks if task.assignee == assignee]
    if search is not None:
        needle = search.lower()
        tasks = [
            task
            for task in tasks
            if needle in task.title.lower() or needle in task.description.lower()
        ]
    return tasks


def get_task_by_id(task_id: str) -> Optional[TaskResponse]:
    return _tasks.get(task_id)


def update_task(task_id: str, payload: TaskUpdate) -> Optional[TaskResponse]:
    existing = _tasks.get(task_id)
    if existing is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return existing

    updated = existing.model_copy(update=updates)
    updated = updated.model_copy(update={"updated_at": datetime.now(timezone.utc)})
    _tasks[task_id] = updated
    return updated


def delete_task(task_id: str) -> bool:
    if task_id in _tasks:
        del _tasks[task_id]
        _comments.pop(task_id, None)
        return True
    return False


def add_comment(task_id: str, payload: CommentCreate) -> CommentResponse:
    comment = CommentResponse(
        id=str(uuid4()),
        task_id=task_id,
        text=payload.text,
        created_at=datetime.now(timezone.utc),
        edited_at=None,
    )
    _comments.setdefault(task_id, []).append(comment)
    return comment


def get_comments(task_id: str) -> list[CommentResponse]:
    return list(_comments.get(task_id, []))


def update_comment(
    task_id: str, comment_id: str, payload: CommentUpdate
) -> Optional[CommentResponse]:
    comments = _comments.get(task_id, [])
    for index, comment in enumerate(comments):
        if comment.id == comment_id:
            updated = comment.model_copy(
                update={"text": payload.text, "edited_at": datetime.now(timezone.utc)}
            )
            comments[index] = updated
            return updated
    return None


def delete_comment(task_id: str, comment_id: str) -> bool:
    comments = _comments.get(task_id, [])
    for index, comment in enumerate(comments):
        if comment.id == comment_id:
            del comments[index]
            return True
    return False


def _reset() -> None:
    _tasks.clear()
    _comments.clear()
