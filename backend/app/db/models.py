from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    event,
    insert,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base, utcnow_iso


class ProjectStatus(str, PyEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectMemberRole(str, PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class TaskStatus(str, PyEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class TaskPriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MilestoneStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class DocumentProcessingStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRunStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class IntegrationProvider(str, PyEnum):
    GITHUB = "github"
    GOOGLE_CALENDAR = "google_calendar"
    GMAIL = "gmail"
    SLACK = "slack"


def _json_type():
    return JSON().with_variant(JSONB(), "postgresql")


def _enum_column(enum_type: type[PyEnum], name: str):
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(String(255), default=utcnow_iso)
    updated_at = Column(String(255), default=utcnow_iso, onupdate=utcnow_iso)
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    long_term_memories = relationship(
        "LongTermMemory",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    google_sub = Column(String(255), unique=True, nullable=True)
    projects_created = relationship(
        "Project",
        back_populates="creator",
        foreign_keys="Project.created_by",
    )
    project_memberships = relationship(
        "ProjectMember",
        back_populates="user",
        foreign_keys="ProjectMember.user_id",
    )
    assigned_tasks = relationship(
        "Task",
        back_populates="assignee",
        foreign_keys="Task.assignee_id",
    )
    created_tasks = relationship(
        "Task",
        back_populates="creator",
        foreign_keys="Task.created_by",
    )
    organizations_created = relationship(
        "Organization",
        back_populates="creator",
        foreign_keys="Organization.created_by",
    )
    organization_memberships = relationship(
        "OrganizationMember",
        back_populates="user",
        foreign_keys="OrganizationMember.user_id",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, ForeignKey("conversations.thread_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(String(255), default=utcnow_iso)
    updated_at = Column(String(255), default=utcnow_iso, onupdate=utcnow_iso)

    conversation = relationship("Conversation", back_populates="messages")

class LongTermMemory(Base):
    __tablename__ = "long_term_memory"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, ForeignKey("conversations.thread_id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(String(255), default=utcnow_iso)
    updated_at = Column(String(255), default=utcnow_iso, onupdate=utcnow_iso)

    conversation = relationship("Conversation", back_populates="long_term_memories")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        _enum_column(ProjectStatus, "project_status"),
        nullable=False,
        default=ProjectStatus.ACTIVE,
    )
    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    created_at = Column(String(255), default=utcnow_iso, nullable=False)
    updated_at = Column(
        String(255),
        default=utcnow_iso,
        onupdate=utcnow_iso,
        nullable=False,
    )

    creator = relationship(
        "User",
        back_populates="projects_created",
        foreign_keys=[created_by],
    )
    organization = relationship("Organization", back_populates="projects")
    members = relationship(
        "ProjectMember",
        back_populates="project",
        foreign_keys="ProjectMember.project_id",
    )
    tasks = relationship(
        "Task",
        back_populates="project",
        foreign_keys="Task.project_id",
    )
    milestones = relationship("Milestone", back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_members_project_user",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    role = Column(
        _enum_column(ProjectMemberRole, "project_member_role"),
        nullable=False,
        default=ProjectMemberRole.MEMBER,
    )
    joined_at = Column(String(255), default=utcnow_iso, nullable=False)

    project = relationship(
        "Project",
        back_populates="members",
        foreign_keys=[project_id],
    )
    user = relationship(
        "User",
        back_populates="project_memberships",
        foreign_keys=[user_id],
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_tasks_id_project"),
        ForeignKeyConstraint(
            ["project_id", "assignee_id"],
            ["project_members.project_id", "project_members.user_id"],
            name="fk_tasks_project_assignee_membership",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    milestone_id = Column(
        Integer,
        ForeignKey("milestones.id"),
        nullable=True,
        index=True,
    )
    assignee_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        _enum_column(TaskStatus, "task_status"),
        nullable=False,
        default=TaskStatus.TODO,
        index=True,
    )
    priority = Column(
        _enum_column(TaskPriority, "task_priority"),
        nullable=False,
        default=TaskPriority.MEDIUM,
        index=True,
    )
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(String(255), default=utcnow_iso, nullable=False)
    updated_at = Column(
        String(255),
        default=utcnow_iso,
        onupdate=utcnow_iso,
        nullable=False,
    )

    project = relationship(
        "Project",
        back_populates="tasks",
        foreign_keys=[project_id],
    )
    milestone = relationship("Milestone", back_populates="tasks")
    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        overlaps="task",
    )
    dependents = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        overlaps="depends_on",
    )
    assignee = relationship(
        "User",
        back_populates="assigned_tasks",
        foreign_keys=[assignee_id],
    )
    creator = relationship(
        "User",
        back_populates="created_tasks",
        foreign_keys=[created_by],
    )


@event.listens_for(Project, "after_insert")
def _create_creator_membership(mapper, connection, project) -> None:
    connection.execute(
        insert(ProjectMember).values(
            project_id=project.id,
            user_id=project.created_by,
            role=ProjectMemberRole.OWNER.value,
        )
    )


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    creator = relationship("User", back_populates="organizations_created", foreign_keys=[created_by])
    members = relationship("OrganizationMember", back_populates="organization")
    projects = relationship("Project", back_populates="organization")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(_enum_column(ProjectMemberRole, "organization_member_role"), nullable=False,
                  default=ProjectMemberRole.MEMBER)
    joined_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organization_memberships", foreign_keys=[user_id])


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(_enum_column(MilestoneStatus, "milestone_status"), nullable=False,
                    default=MilestoneStatus.PENDING, index=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    project = relationship("Project", back_populates="milestones")
    tasks = relationship("Task", back_populates="milestone")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependencies_pair"),
        CheckConstraint("task_id <> depends_on_task_id", name="ck_task_dependencies_not_self"),
        ForeignKeyConstraint(
            ["task_id", "project_id"],
            ["tasks.id", "tasks.project_id"],
            name="fk_task_dependencies_task_project",
        ),
        ForeignKeyConstraint(
            ["depends_on_task_id", "project_id"],
            ["tasks.id", "tasks.project_id"],
            name="fk_task_dependencies_dependency_project",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    depends_on_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    project_id = Column(Integer, nullable=False, index=True)
    dependency_type = Column(String(50), nullable=False, default="blocks")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    task = relationship("Task", foreign_keys=[task_id], overlaps="dependencies")
    depends_on = relationship("Task", foreign_keys=[depends_on_task_id], overlaps="dependents")


@event.listens_for(Organization, "after_insert")
def _create_organization_owner(mapper, connection, organization) -> None:
    connection.execute(
        insert(OrganizationMember).values(
            organization_id=organization.id,
            user_id=organization.created_by,
            role=ProjectMemberRole.OWNER.value,
        )
    )


class ProjectDocument(Base):
    __tablename__ = "project_documents"
    __table_args__ = (
        UniqueConstraint("project_id", "checksum", name="uq_project_documents_project_checksum"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    mime_type = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    processing_status = Column(
        _enum_column(DocumentProcessingStatus, "document_processing_status"),
        nullable=False, default=DocumentProcessingStatus.PENDING, index=True,
    )
    checksum = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    project = relationship("Project")
    uploader = relationship("User", foreign_keys=[uploaded_by])


class MeetingNote(Base):
    __tablename__ = "meeting_notes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    meeting_date = Column(DateTime(timezone=True), nullable=False)
    raw_content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    project = relationship("Project")
    creator = relationship("User", foreign_keys=[created_by])


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (UniqueConstraint("organization_id", "idempotency_key",
                                       name="uq_agent_runs_org_idempotency"),)

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal = Column(Text, nullable=False)
    status = Column(_enum_column(AgentRunStatus, "agent_run_status"), nullable=False,
                    default=AgentRunStatus.PENDING, index=True)
    execution_plan = Column(_json_type(), nullable=True)
    result = Column(_json_type(), nullable=True)
    error_summary = Column(Text, nullable=True)
    graph_thread_id = Column(String(255), nullable=True, index=True)
    idempotency_key = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    organization = relationship("Organization")
    project = relationship("Project")
    requester = relationship("User", foreign_keys=[requested_by])
    approvals = relationship("AgentApproval", back_populates="agent_run")
    events = relationship("AgentEvent", back_populates="agent_run")
    artifacts = relationship("AgentArtifact", back_populates="agent_run")


class AgentApproval(Base):
    __tablename__ = "agent_approvals"

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action_type = Column(String(100), nullable=False)
    action_payload = Column(_json_type(), nullable=False)
    status = Column(_enum_column(ApprovalStatus, "approval_status"), nullable=False,
                    default=ApprovalStatus.PENDING, index=True)
    decision_note = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    decided_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    agent_run = relationship("AgentRun", back_populates="approvals")
    requester = relationship("User", foreign_keys=[requested_by])
    approver = relationship("User", foreign_keys=[approver_id])


class AgentEvent(Base):
    __tablename__ = "agent_events"
    __table_args__ = (UniqueConstraint("agent_run_id", "sequence_number",
                                       name="uq_agent_events_run_sequence"),)

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_payload = Column(_json_type(), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    agent_run = relationship("AgentRun", back_populates="events")


class AgentArtifact(Base):
    __tablename__ = "agent_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    artifact_type = Column(String(50), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    mime_type = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    agent_run = relationship("AgentRun", back_populates="artifacts")
    project = relationship("Project")
    creator = relationship("User", foreign_keys=[created_by])


class AgentSchedule(Base):
    __tablename__ = "agent_schedules"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    schedule_type = Column(String(50), nullable=False)
    schedule_config = Column(_json_type(), nullable=False)
    timezone = Column(String(64), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    organization = relationship("Organization")
    project = relationship("Project")
    creator = relationship("User", foreign_keys=[created_by])


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"
    __table_args__ = (UniqueConstraint("organization_id", "provider", "external_account_id",
                                       name="uq_integration_connection_account"),)

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    connected_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(_enum_column(IntegrationProvider, "integration_provider"), nullable=False)
    external_account_id = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    granted_scopes = Column(_json_type(), nullable=False)
    connection_status = Column(String(50), nullable=False, default="active", index=True)
    credential_reference = Column(String(1024), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    organization = relationship("Organization")
    connector = relationship("User", foreign_keys=[connected_by])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=False)
    before_state = Column(_json_type(), nullable=True)
    after_state = Column(_json_type(), nullable=True)
    request_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    organization = relationship("Organization")
    project = relationship("Project")
    actor = relationship("User", foreign_keys=[actor_id])