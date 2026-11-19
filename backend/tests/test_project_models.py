from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    Organization,
    Project,
    ProjectMember,
    ProjectMemberRole,
    Task,
    TaskPriority,
    TaskStatus,
    User,
)


@pytest.fixture
def project_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with TestSessionLocal() as db:
        creator = User(username="creator", password_hash="hash")
        assignee = User(username="assignee", password_hash="hash")
        db.add_all([creator, assignee])
        db.commit()
        yield db, creator, assignee

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _project(db, creator):
    organization = Organization(
        name="Acme",
        slug="acme",
        created_by=creator.id,
    )
    db.add(organization)
    db.flush()
    project = Project(
        organization_id=organization.id,
        name="Launch",
        description="Release project",
        created_by=creator.id,
    )
    db.add(project)
    db.flush()
    return project


def test_project_creation_and_creator_relationship(project_db):
    db, creator, _ = project_db

    project = _project(db, creator)
    db.commit()

    assert project.creator.id == creator.id
    assert db.query(Project).filter_by(created_by=creator.id).one() == project
    membership = db.query(ProjectMember).filter_by(project_id=project.id).one()
    assert membership.user_id == creator.id
    assert membership.role == ProjectMemberRole.OWNER


def test_project_membership_and_duplicate_prevention(project_db):
    db, creator, assignee = project_db
    project = _project(db, creator)

    db.add(
        ProjectMember(
            project_id=project.id,
            user_id=assignee.id,
            role=ProjectMemberRole.MEMBER,
        )
    )
    db.commit()

    duplicate = ProjectMember(project_id=project.id, user_id=assignee.id)
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_task_creation_relationships_and_optional_assignment(project_db):
    db, creator, assignee = project_db
    project = _project(db, creator)
    db.add(ProjectMember(project_id=project.id, user_id=assignee.id))
    db.flush()

    assigned = Task(
        project_id=project.id,
        assignee_id=assignee.id,
        created_by=creator.id,
        title="Prepare release",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        due_date=datetime(2026, 12, 1, tzinfo=timezone.utc),
    )
    unassigned = Task(
        project_id=project.id,
        created_by=creator.id,
        title="Review notes",
    )
    db.add_all([assigned, unassigned])
    db.commit()

    assert assigned.project.id == project.id
    assert assigned.assignee.id == assignee.id
    assert unassigned.assignee is None
    assert {task.id for task in project.tasks} == {assigned.id, unassigned.id}


def test_invalid_task_status_and_priority_are_rejected(project_db):
    db, creator, _ = project_db
    project = _project(db, creator)

    invalid_status = Task(
        project_id=project.id,
        created_by=creator.id,
        title="Invalid status",
        status="not-a-status",
    )
    db.add(invalid_status)
    with pytest.raises(StatementError):
        db.commit()
    db.rollback()

    invalid_priority = Task(
        project_id=project.id,
        created_by=creator.id,
        title="Invalid priority",
        priority="not-a-priority",
    )
    db.add(invalid_priority)
    with pytest.raises(StatementError):
        db.commit()


def test_assignee_must_be_a_project_member(project_db):
    db, creator, assignee = project_db
    project = _project(db, creator)
    task = Task(
        project_id=project.id,
        assignee_id=assignee.id,
        created_by=creator.id,
        title="Unassignable task",
    )
    db.add(task)

    with pytest.raises(IntegrityError):
        db.commit()
