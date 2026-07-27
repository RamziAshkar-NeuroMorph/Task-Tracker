from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.models import TaskCreate, TaskResponse, TaskUpdate

_tasks: dict[str, TaskResponse] = {}


def add_task(payload: TaskCreate) -> TaskResponse:
    """Store a new task and return the stored record.

    Assigns the three server-owned fields: ``id`` is a fresh uuid4 rendered as a
    string, and ``created_at`` and ``updated_at`` are both set to the same
    timezone-aware UTC instant.

    A ``None`` description is normalized to the empty string, because
    ``TaskResponse.description`` is a non-optional ``str``.

    Args:
        payload: The validated creation request. Its ``status`` and ``priority``
            are copied through as given; this layer applies no transition rules.

    Returns:
        TaskResponse: The newly stored task.
    """
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


def get_all_tasks(status=None, priority=None) -> list[TaskResponse]:
    """Return stored tasks, optionally filtered by status and/or priority.

    Filters are applied in sequence, so passing both narrows to tasks matching
    both. Each filter compares with ``==`` against the corresponding task field.

    Neither parameter is annotated, so this function does not itself constrain
    what may be passed; the enum constraint comes from the route signature in
    :func:`app.main.list_tasks`.

    Args:
        status: Optional value to match against each task's ``status``. ``None``
            disables the filter.
        priority: Optional value to match against each task's ``priority``.
            ``None`` disables the filter.

    Returns:
        list[TaskResponse]: A new list of the matching tasks, in insertion
        order. Empty when nothing matches.
    """
    tasks = list(_tasks.values())
    if status is not None:
        tasks = [task for task in tasks if task.status == status]
    if priority is not None:
        tasks = [task for task in tasks if task.priority == priority]
    return tasks


def get_task_by_id(task_id: str) -> Optional[TaskResponse]:
    """Look up a single task by id.

    Signals absence by return value rather than by raising; translating a miss
    into an HTTP 404 is :mod:`app.main`'s responsibility.

    Args:
        task_id: The id to look up.

    Returns:
        Optional[TaskResponse]: The stored task, or ``None`` if no task holds
        that id.
    """
    return _tasks.get(task_id)


def update_task(task_id: str, payload: TaskUpdate) -> Optional[TaskResponse]:
    """Apply a partial update to a stored task.

    Only fields explicitly set on the payload are applied, via
    ``model_dump(exclude_unset=True)``. A field left out of the request body is
    therefore untouched, which is distinct from sending it explicitly.

    When the payload sets no fields at all, the existing record is returned
    as-is and ``updated_at`` is *not* advanced. Otherwise the record is replaced
    with a copy rather than mutated in place, and ``updated_at`` is refreshed to
    the current UTC instant.

    Args:
        task_id: The id of the task to update.
        payload: The partial update. Every field is optional.

    Returns:
        Optional[TaskResponse]: The updated task, the unchanged existing task
        when the payload set no fields, or ``None`` if no task holds that id.
    """
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
    """Delete a task by id.

    Signals the outcome by return value rather than by raising; translating a
    miss into an HTTP 404 is :mod:`app.main`'s responsibility.

    Args:
        task_id: The id of the task to delete.

    Returns:
        bool: ``True`` if a task was found and removed, ``False`` if no task
        held that id.
    """
    if task_id in _tasks:
        del _tasks[task_id]
        return True
    return False


def _reset() -> None:
    """Clear all stored tasks.

    Test-support hook, invoked by the autouse ``_reset_storage`` fixture in
    ``tests/conftest.py`` before and after every test. Because the store is
    module-level state, any additional module-level state added to this module
    must also be cleared here or it will leak between tests.

    Returns:
        None
    """
    _tasks.clear()
