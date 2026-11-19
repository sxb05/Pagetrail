from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    AgentApproval,
    AgentArtifact,
    AgentEvent,
    AgentRun,
    AgentRunStatus,
    AuditLog,
    IntegrationConnection,
    IntegrationProvider,
    MeetingNote,
    Milestone,
    MilestoneStatus,
    Organization,
    OrganizationMember,
    Project,
    ProjectDocument,
    ProjectMember,
    Task,
    TaskDependency,
    User,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def _fixture(db):
    owner = User(username="ops-owner", password_hash="hash")
    member = User(username="ops-member", password_hash="hash")
    db.add_all([owner, member])
    db.flush()
    organization = Organization(name="Operations", slug="operations", created_by=owner.id)
    db.add(organization)
    db.flush()
    db.add(OrganizationMember(organization_id=organization.id, user_id=member.id))
    project = Project(
        organization_id=organization.id,
        name="Migration",
        created_by=owner.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=member.id))
    db.flush()
    return owner, member, organization, project


def test_organization_project_milestone_and_dependency_constraints(db):
    owner, member, organization, project = _fixture(db)
    milestone = Milestone(
        project_id=project.id,
        title="Phase one",
        status=MilestoneStatus.IN_PROGRESS,
    )
    db.add(milestone)
    db.flush()
    first = Task(project_id=project.id, created_by=owner.id, title="First")
    second = Task(
        project_id=project.id,
        assignee_id=member.id,
        created_by=owner.id,
        milestone_id=milestone.id,
        title="Second",
    )
    db.add_all([first, second])
    db.flush()
    dependency = TaskDependency(
        task_id=second.id,
        depends_on_task_id=first.id,
        project_id=project.id,
    )
    db.add(dependency)
    db.commit()

    assert organization.members[0].user_id == owner.id
    assert project.tasks[1].milestone.id == milestone.id
    assert dependency.depends_on.id == first.id

    db.add(TaskDependency(task_id=first.id, depends_on_task_id=first.id, project_id=project.id))
    with pytest.raises(IntegrityError):
        db.commit()


def test_project_operations_metadata_models_and_json_payloads(db):
    owner, _, organization, project = _fixture(db)
    run = AgentRun(
        organization_id=organization.id,
        project_id=project.id,
        requested_by=owner.id,
        goal="Prepare report",
        execution_plan={"steps": ["collect"]},
        status=AgentRunStatus.RUNNING,
    )
    db.add(run)
    db.flush()
    db.add_all(
        [
            AgentApproval(
                agent_run_id=run.id,
                requested_by=owner.id,
                action_type="generate_report",
                action_payload={"format": "pdf"},
            ),
            AgentEvent(
                agent_run_id=run.id,
                event_type="plan_created",
                event_payload={"step": 1},
                sequence_number=1,
            ),
            AgentArtifact(
                agent_run_id=run.id,
                project_id=project.id,
                created_by=owner.id,
                name="report.pdf",
                artifact_type="pdf",
                storage_path="reports/report.pdf",
                mime_type="application/pdf",
            ),
            ProjectDocument(
                project_id=project.id,
                uploaded_by=owner.id,
                filename="requirements.md",
                storage_path="projects/requirements.md",
                mime_type="text/markdown",
                file_size=100,
                checksum="abc123",
            ),
            MeetingNote(
                project_id=project.id,
                created_by=owner.id,
                title="Kickoff",
                meeting_date=datetime(2026, 11, 19, tzinfo=timezone.utc),
                raw_content="Notes",
            ),
            IntegrationConnection(
                organization_id=organization.id,
                connected_by=owner.id,
                provider=IntegrationProvider.GITHUB,
                external_account_id="account-1",
                granted_scopes=["repo"],
                credential_reference="secret://github/account-1",
            ),
            AuditLog(
                organization_id=organization.id,
                project_id=project.id,
                actor_id=owner.id,
                action="agent.run",
                resource_type="agent_run",
                resource_id=str(run.id),
                after_state={"status": "running"},
            ),
        ]
    )
    db.commit()

    assert len(run.events) == 1
    assert run.approvals[0].action_payload["format"] == "pdf"
