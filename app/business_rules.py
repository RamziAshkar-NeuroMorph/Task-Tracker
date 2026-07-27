from fastapi import HTTPException, status

from app.models import TaskStatus

VALID_TRANSITIONS: frozenset[tuple[TaskStatus, TaskStatus]] = frozenset({
    (TaskStatus.TODO, TaskStatus.IN_PROGRESS),
    (TaskStatus.IN_PROGRESS, TaskStatus.DONE),
    (TaskStatus.DONE, TaskStatus.IN_PROGRESS),
    (TaskStatus.DONE, TaskStatus.DONE),
    (TaskStatus.IN_PROGRESS, TaskStatus.IN_PROGRESS),
    (TaskStatus.TODO, TaskStatus.TODO),
})


def validate_status_transition(current: TaskStatus, new: TaskStatus) -> None:
    """Reject a status change that is not in the allowed transition table.

    Membership in :data:`VALID_TRANSITIONS` is the whole rule: the six listed
    ``(current, new)`` pairs pass and every other combination fails. The three
    self-transitions are listed explicitly, so re-sending a task's current
    status is permitted. ``ToDo -> Done`` and any move back to ``ToDo`` are not
    in the table and are therefore rejected.

    Args:
        current: The task's status as currently stored.
        new: The status being requested.

    Returns:
        None: Returns without effect when the transition is allowed. The caller
        is expected to proceed with the write only if this call returns.

    Raises:
        HTTPException: 422 when the pair is absent from the table. The detail
            names both statuses and appends the sorted list of allowed
            ``"From->To"`` strings, for example ``"Invalid status transition
            from ToDo to Done. Allowed transitions: ['Done->Done', ...]"``.
    """
    if (current, new) not in VALID_TRANSITIONS:
        allowed = sorted({f"{f.value}->{t.value}" for f, t in VALID_TRANSITIONS})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status transition from {current.value} to {new.value}. Allowed transitions: {allowed}",
        )
