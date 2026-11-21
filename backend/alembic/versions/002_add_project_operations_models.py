"""Add project operations tables missing from production.

Revision ID: 002_project_operations
Revises: 001_existing_production
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "002_project_operations"
down_revision = "001_existing_production"
branch_labels = None
depends_on = None


def _enum(name: str, values: list[str]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_organizations_id", "organizations", ["id"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    op.create_index("ix_organizations_created_by", "organizations", ["created_by"])

    op.create_table(
        "organization_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", _enum("organization_member_role", ["owner", "admin", "member"]), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
    )
    op.create_index("ix_organization_members_id", "organization_members", ["id"])
    op.create_index("ix_organization_members_organization_id", "organization_members", ["organization_id"])
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _enum("project_status", ["active", "completed", "archived"]), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_id", "projects", ["id"])
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])
    op.create_index("ix_projects_created_by", "projects", ["created_by"])

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", _enum("project_member_role", ["owner", "admin", "member"]), nullable=False),
        sa.Column("joined_at", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )
    op.create_index("ix_project_members_id", "project_members", ["id"])
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])

    op.create_table(
        "milestones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _enum("milestone_status", ["pending", "in_progress", "completed"]), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_milestones_id", "milestones", ["id"])
    op.create_index("ix_milestones_project_id", "milestones", ["project_id"])
    op.create_index("ix_milestones_status", "milestones", ["status"])
    op.create_index("ix_milestones_due_date", "milestones", ["due_date"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("milestone_id", sa.Integer(), nullable=True),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _enum("task_status", ["todo", "in_progress", "blocked", "done"]), nullable=False),
        sa.Column("priority", _enum("task_priority", ["low", "medium", "high", "urgent"]), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["milestone_id"], ["milestones.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id", "assignee_id"], ["project_members.project_id", "project_members.user_id"], name="fk_tasks_project_assignee_membership"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "project_id", name="uq_tasks_id_project"),
    )
    op.create_index("ix_tasks_id", "tasks", ["id"])
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_milestone_id", "tasks", ["milestone_id"])
    op.create_index("ix_tasks_assignee_id", "tasks", ["assignee_id"])
    op.create_index("ix_tasks_created_by", "tasks", ["created_by"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"])

    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("depends_on_task_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("dependency_type", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["depends_on_task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["task_id", "project_id"], ["tasks.id", "tasks.project_id"], name="fk_task_dependencies_task_project"),
        sa.ForeignKeyConstraint(["depends_on_task_id", "project_id"], ["tasks.id", "tasks.project_id"], name="fk_task_dependencies_dependency_project"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependencies_pair"),
        sa.CheckConstraint("task_id <> depends_on_task_id", name="ck_task_dependencies_not_self"),
    )
    op.create_index("ix_task_dependencies_id", "task_dependencies", ["id"])
    op.create_index("ix_task_dependencies_task_id", "task_dependencies", ["task_id"])
    op.create_index("ix_task_dependencies_depends_on_task_id", "task_dependencies", ["depends_on_task_id"])
    op.create_index("ix_task_dependencies_project_id", "task_dependencies", ["project_id"])

    op.create_table(
        "project_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("processing_status", _enum("document_processing_status", ["pending", "processing", "completed", "failed"]), nullable=False),
        sa.Column("checksum", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "checksum", name="uq_project_documents_project_checksum"),
    )
    op.create_index("ix_project_documents_id", "project_documents", ["id"])
    op.create_index("ix_project_documents_project_id", "project_documents", ["project_id"])
    op.create_index("ix_project_documents_uploaded_by", "project_documents", ["uploaded_by"])
    op.create_index("ix_project_documents_processing_status", "project_documents", ["processing_status"])

    op.create_table(
        "meeting_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("meeting_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meeting_notes_id", "meeting_notes", ["id"])
    op.create_index("ix_meeting_notes_project_id", "meeting_notes", ["project_id"])
    op.create_index("ix_meeting_notes_created_by", "meeting_notes", ["created_by"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", _enum("agent_run_status", ["pending", "running", "waiting_for_approval", "completed", "failed", "cancelled"]), nullable=False),
        sa.Column("execution_plan", JSONB(), nullable=True),
        sa.Column("result", JSONB(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("graph_thread_id", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_agent_runs_org_idempotency"),
    )
    op.create_index("ix_agent_runs_id", "agent_runs", ["id"])
    op.create_index("ix_agent_runs_organization_id", "agent_runs", ["organization_id"])
    op.create_index("ix_agent_runs_project_id", "agent_runs", ["project_id"])
    op.create_index("ix_agent_runs_requested_by", "agent_runs", ["requested_by"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    op.create_index("ix_agent_runs_graph_thread_id", "agent_runs", ["graph_thread_id"])

    op.create_table(
        "agent_approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_run_id", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("action_payload", JSONB(), nullable=False),
        sa.Column("status", _enum("approval_status", ["pending", "approved", "rejected", "expired"]), nullable=False),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_approvals_id", "agent_approvals", ["id"])
    op.create_index("ix_agent_approvals_agent_run_id", "agent_approvals", ["agent_run_id"])
    op.create_index("ix_agent_approvals_requested_by", "agent_approvals", ["requested_by"])
    op.create_index("ix_agent_approvals_approver_id", "agent_approvals", ["approver_id"])
    op.create_index("ix_agent_approvals_status", "agent_approvals", ["status"])
    op.create_index("ix_agent_approvals_expires_at", "agent_approvals", ["expires_at"])

    op.create_table(
        "agent_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_run_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_payload", JSONB(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_run_id", "sequence_number", name="uq_agent_events_run_sequence"),
    )
    op.create_index("ix_agent_events_id", "agent_events", ["id"])
    op.create_index("ix_agent_events_agent_run_id", "agent_events", ["agent_run_id"])
    op.create_index("ix_agent_events_event_type", "agent_events", ["event_type"])

    op.create_table(
        "agent_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_run_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_artifacts_id", "agent_artifacts", ["id"])
    op.create_index("ix_agent_artifacts_agent_run_id", "agent_artifacts", ["agent_run_id"])
    op.create_index("ix_agent_artifacts_project_id", "agent_artifacts", ["project_id"])
    op.create_index("ix_agent_artifacts_created_by", "agent_artifacts", ["created_by"])

    op.create_table(
        "agent_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("schedule_type", sa.String(50), nullable=False),
        sa.Column("schedule_config", JSONB(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_schedules_id", "agent_schedules", ["id"])
    op.create_index("ix_agent_schedules_organization_id", "agent_schedules", ["organization_id"])
    op.create_index("ix_agent_schedules_project_id", "agent_schedules", ["project_id"])
    op.create_index("ix_agent_schedules_created_by", "agent_schedules", ["created_by"])
    op.create_index("ix_agent_schedules_enabled", "agent_schedules", ["enabled"])
    op.create_index("ix_agent_schedules_next_run_at", "agent_schedules", ["next_run_at"])

    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("connected_by", sa.Integer(), nullable=False),
        sa.Column("provider", _enum("integration_provider", ["github", "google_calendar", "gmail", "slack"]), nullable=False),
        sa.Column("external_account_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("granted_scopes", JSONB(), nullable=False),
        sa.Column("connection_status", sa.String(50), nullable=False),
        sa.Column("credential_reference", sa.String(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["connected_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "provider", "external_account_id", name="uq_integration_connection_account"),
    )
    op.create_index("ix_integration_connections_id", "integration_connections", ["id"])
    op.create_index("ix_integration_connections_organization_id", "integration_connections", ["organization_id"])
    op.create_index("ix_integration_connections_connected_by", "integration_connections", ["connected_by"])
    op.create_index("ix_integration_connections_provider", "integration_connections", ["provider"])
    op.create_index("ix_integration_connections_connection_status", "integration_connections", ["connection_status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column("before_state", JSONB(), nullable=True),
        sa.Column("after_state", JSONB(), nullable=True),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_project_id", "audit_logs", ["project_id"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])


def downgrade() -> None:
    raise RuntimeError("Downgrade is intentionally disabled: dropping new tables could destroy data.")

