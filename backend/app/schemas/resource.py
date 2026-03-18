"""Resource schemas."""

from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from app.db.models.resource import ResourceType, SummaryStatus
from app.schemas.base import BaseSchema, TimestampSchema


class ResourceCreate(BaseSchema):
    """Schema for creating a resource."""

    title: str = Field(max_length=200)
    type: ResourceType
    url: str | None = Field(default=None, max_length=2000)
    subject_id: UUID | None = None


class ResourceResponse(BaseSchema, TimestampSchema):
    """Schema for reading a resource."""

    id: UUID
    title: str
    type: str
    file_path: str | None
    url: str | None
    content: str | None
    summary: str | None
    summary_status: str
    file_size_bytes: int | None
    page_count: int | None
    subject_id: UUID | None
    user_id: UUID

    @field_validator("type", mode="before")
    @classmethod
    def convert_type(cls, v):
        if isinstance(v, ResourceType):
            return v.value
        return str(v)

    @field_validator("summary_status", mode="before")
    @classmethod
    def convert_summary_status(cls, v):
        if isinstance(v, SummaryStatus):
            return v.value
        return str(v)


class ResourceSummaryResponse(BaseSchema):
    """Schema for resource summary response."""

    id: UUID
    title: str
    summary: str | None
    summary_status: str

    @field_validator("summary_status", mode="before")
    @classmethod
    def convert_summary_status(cls, v):
        if isinstance(v, SummaryStatus):
            return v.value
        return str(v)
