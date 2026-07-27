from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TaskStatus(str, Enum):
    TODO = "ToDo"
    IN_PROGRESS = "InProgress"
    DONE = "Done"


class TaskPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: Optional[str] = ""
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        """Normalize and check the title on task creation.

        Surrounding whitespace is stripped first, and the stripped form is what
        gets stored - both checks below and the return value operate on it.

        Args:
            value: The raw title from the request body.

        Returns:
            str: The title with leading and trailing whitespace removed.

        Raises:
            ValueError: If the title is empty once stripped, or if the stripped
                title exceeds 200 characters. Pydantic converts this into the
                422 response the client sees.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title must not be blank.")
        if len(stripped) > 200:
            raise ValueError("Title must be 200 characters or fewer.")
        return stripped


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        """Normalize and check the title on a partial update.

        Mirrors :meth:`TaskCreate.validate_title`, with one difference that is
        the reason the two are not shared: ``None`` is passed straight through
        untouched, since on this model it means "field not being updated".
        Keep the two in sync when either changes.

        Args:
            value: The raw title from the request body, or ``None``.

        Returns:
            Optional[str]: ``None`` unchanged, otherwise the title with leading
            and trailing whitespace removed.

        Raises:
            ValueError: If a non-``None`` title is empty once stripped, or if
                the stripped title exceeds 200 characters. Pydantic converts
                this into the 422 response the client sees.
        """
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title must not be blank.")
        if len(stripped) > 200:
            raise ValueError("Title must be 200 characters or fewer.")
        return stripped


class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee: Optional[str]
    created_at: datetime
    updated_at: datetime
