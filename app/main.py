from datetime import datetime, timezone
from app.business_rules import validate_status_transition
from app.models import TaskCreate, TaskResponse, TaskStatus, TaskPriority, TaskUpdate
from app import storage
from fastapi import FastAPI, HTTPException, status
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
    """Report that the API process is alive.

    Performs no dependency checks: the response is constructed unconditionally,
    so a 200 means the process is serving requests and nothing more.

    Returns:
        dict: A mapping with two keys - ``status``, always the literal string
        ``"ok"``, and ``timestamp``, the current UTC time as a timezone-aware
        ISO 8601 string.

    Example:
        ``GET /health`` responds ``200 OK``::

            {
                "status": "ok",
                "timestamp": "2026-07-27T10:23:22.366203+00:00"
            }
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["tasks"])
def create_task(payload: TaskCreate) -> TaskResponse:
    """Create a task and return it with its server-assigned fields.

    Delegates directly to :func:`app.storage.add_task`; ``id``, ``created_at``
    and ``updated_at`` are generated there and cannot be supplied by the client.

    Note that ``status`` is an accepted field on ``TaskCreate``, so a task may
    be created directly in any of the three statuses. The transition table in
    :mod:`app.business_rules` governs PATCH only and is not consulted here.

    Args:
        payload: Validated request body. ``title`` is required; ``description``
            defaults to ``""``, ``status`` to ``ToDo``, ``priority`` to
            ``Medium``, and ``assignee`` to ``None``.

    Returns:
        TaskResponse: The stored task, serialized with HTTP 201.

    Raises:
        fastapi.exceptions.RequestValidationError: Returned to the client as
            422 when the body fails ``TaskCreate`` validation - a blank or
            over-200-character ``title``, an unknown status or priority value,
            or any unknown field (every model sets ``extra="forbid"``).

    Example:
        ``POST /tasks`` with ``{"title": "Verify container", "priority": "High"}``
        responds ``201 Created``::

            {
                "id": "31f4254b-3cf8-4825-b5eb-6704690cfcd4",
                "title": "Verify container",
                "description": "",
                "status": "ToDo",
                "priority": "High",
                "assignee": null,
                "created_at": "2026-07-27T10:25:29.200102Z",
                "updated_at": "2026-07-27T10:25:29.200102Z"
            }
    """
    return storage.add_task(payload)


@app.get("/tasks", response_model=list[TaskResponse], tags=["tasks"])
def list_tasks(
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
) -> list[TaskResponse]:
    """List tasks, optionally narrowed by status and/or priority.

    Both filters are optional query parameters. When both are supplied they are
    combined with AND. There is no pagination and no sort parameter; tasks come
    back in the order the underlying store yields them.

    Args:
        status: Optional exact-match filter on the task status. Omit to include
            every status.
        priority: Optional exact-match filter on the task priority. Omit to
            include every priority.

    Returns:
        list[TaskResponse]: Matching tasks, empty if none match or none exist.

    Raises:
        fastapi.exceptions.RequestValidationError: Returned as 422 when a query
            parameter is not one of the permitted enum values.

    Example:
        ``GET /tasks?status=InProgress&priority=High`` responds ``200 OK`` with
        a JSON array of task objects, or ``[]`` when nothing matches.
    """
    return storage.get_all_tasks(status=status, priority=priority)


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def get_task(task_id: str) -> TaskResponse:
    """Retrieve a single task by id.

    Args:
        task_id: The task's ``id``, the uuid4 string assigned at creation. Any
            string is accepted by the route; an unrecognized one is simply a
            miss, not a format error.

    Returns:
        TaskResponse: The stored task.

    Raises:
        HTTPException: 404 with detail ``"Task with id {task_id} not found"``
            when no task holds that id.

    Example:
        ``GET /tasks/31f4254b-3cf8-4825-b5eb-6704690cfcd4`` responds ``200 OK``
        with the task object, or ``404 Not Found``::

            {"detail": "Task with id missing-id not found"}
    """
    task = storage.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return task


@app.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def update_task(task_id: str, payload: TaskUpdate) -> TaskResponse:
    """Partially update a task, enforcing the status transition rules.

    Only fields actually present in the request body are applied, so omitting a
    field leaves it untouched. An empty body ``{}`` is accepted and returns the
    task unchanged, without advancing ``updated_at``.

    When the body carries a status, the transition is checked *before* the write
    is attempted, which requires re-fetching the task - hence the existence
    check appears twice. The order is deliberate: an unknown ``task_id`` yields
    404 rather than 422, even if the requested transition would also be invalid.

    Args:
        task_id: The task's ``id``.
        payload: Validated partial update. Every field is optional.

    Returns:
        TaskResponse: The updated task, with ``updated_at`` refreshed whenever
        at least one field was set in the request body.

    Raises:
        HTTPException: 404 with detail ``"Task with id {task_id} not found"``
            when no task holds that id.
        HTTPException: 422 raised by
            :func:`app.business_rules.validate_status_transition` when the
            requested status change is not one of the six permitted pairs. The
            detail names the current and requested status and lists the allowed
            transitions.
        fastapi.exceptions.RequestValidationError: Returned as 422 when the body
            fails ``TaskUpdate`` validation - a blank or over-200-character
            ``title``, an unknown enum value, or any unknown field.

    Example:
        ``PATCH /tasks/{id}`` with ``{"status": "InProgress"}`` on a ``ToDo``
        task responds ``200 OK`` with the updated object. The same request with
        ``{"status": "Done"}`` responds ``422 Unprocessable Entity``::

            {
                "detail": "Invalid status transition from ToDo to Done. Allowed transitions: ['Done->Done', 'Done->InProgress', 'InProgress->Done', 'InProgress->InProgress', 'ToDo->InProgress', 'ToDo->ToDo']"
            }
    """
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
    """Delete a task by id.

    Deletion is not idempotent from the client's perspective: repeating a
    successful delete returns 404 the second time.

    Args:
        task_id: The task's ``id``.

    Returns:
        None: The route is registered with status 204, so a successful delete
        sends no response body.

    Raises:
        HTTPException: 404 with detail ``"Task with id {task_id} not found"``
            when no task holds that id.

    Example:
        ``DELETE /tasks/31f4254b-3cf8-4825-b5eb-6704690cfcd4`` responds
        ``204 No Content`` with an empty body.
    """
    if not storage.delete_task(task_id):
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
