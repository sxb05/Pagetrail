from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OrganizationCreate(ORMModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)


class OrganizationUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)


class OrganizationResponse(ORMModel):
    id: int
    name: str
    slug: str
    created_by: int
    created_at: datetime
    updated_at: datetime


class OrganizationMemberCreate(ORMModel):
    user_id: int
    role: str = "member"


class OrganizationMemberUpdate(ORMModel):
    role: str


class OrganizationMemberResponse(ORMModel):
    id: int
    organization_id: int
    user_id: int
    role: str
    joined_at: datetime


class ProjectCreate(ORMModel):
    organization_id: int
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: str = "active"


class ProjectUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None


class ProjectMemberCreate(ORMModel):
    user_id: int
    role: str = "member"


class ProjectMemberUpdate(ORMModel):
    role: str


class ProjectMemberResponse(ORMModel):
    id: int
    project_id: int
    user_id: int
    role: str
    joined_at: str


class ProjectResponse(ORMModel):
    id: int
    organization_id: int
    name: str
    description: str | None
    status: str
    created_by: int
    created_at: str
    updated_at: str


class TaskCreate(ORMModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"
    assignee_id: int | None = None
    milestone_id: int | None = None
    due_date: datetime | None = None


class TaskUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee_id: int | None = None
    milestone_id: int | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None


class TaskResponse(ORMModel):
    id: int
    project_id: int
    milestone_id: int | None
    assignee_id: int | None
    created_by: int
    title: str
    description: str | None
    status: str
    priority: str
    due_date: datetime | None
    completed_at: datetime | None
    created_at: str
    updated_at: str


class MilestoneCreate(ORMModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: str = "pending"
    start_date: datetime | None = None
    due_date: datetime | None = None


class MilestoneUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None


class MilestoneResponse(ORMModel):
    id: int
    project_id: int
    title: str
    description: str | None
    status: str
    start_date: datetime | None
    due_date: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskDependencyCreate(ORMModel):
    depends_on_task_id: int
    dependency_type: str = "blocks"


class TaskDependencyResponse(ORMModel):
    id: int
    task_id: int
    depends_on_task_id: int
    project_id: int
    dependency_type: str
    created_at: datetime


class MeetingNoteCreate(ORMModel):
    title: str = Field(min_length=1, max_length=255)
    meeting_date: datetime
    raw_content: str = Field(min_length=1)
    summary: str | None = None


class MeetingNoteUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    meeting_date: datetime | None = None
    raw_content: str | None = None
    summary: str | None = None


class MeetingNoteResponse(ORMModel):
    id: int
    project_id: int
    created_by: int
    title: str
    meeting_date: datetime
    raw_content: str
    summary: str | None
    created_at: datetime
    updated_at: datetime


class ProjectDocumentCreate(ORMModel):
    filename: str = Field(min_length=1, max_length=255)
    storage_path: str = Field(min_length=1, max_length=1024)
    mime_type: str = Field(min_length=1, max_length=255)
    file_size: int = Field(ge=0)
    checksum: str = Field(min_length=1, max_length=128)
    processing_status: str = "pending"


class ProjectDocumentResponse(ORMModel):
    id: int
    project_id: int
    uploaded_by: int
    filename: str
    storage_path: str
    mime_type: str
    file_size: int
    processing_status: str
    checksum: str
    created_at: datetime
    updated_at: datetime
