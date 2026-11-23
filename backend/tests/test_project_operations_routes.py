import os

os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-key-at-least-32-characters"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.auth import get_db
from app.db.base import Base
from app.main import app


def test_project_operations_authorization_and_dependency_cycle():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    register = client.post(
        "/api/auth/register",
        json={"username": "owner", "password": "password123"},
    )
    assert register.status_code == 201
    personal_registration_login = client.post(
        "/api/auth/login",
        data={"username": "owner", "password": "password123"},
    )
    personal_headers = {
        "Authorization": f"Bearer {personal_registration_login.json()['access_token']}"
    }
    personal_orgs = client.get("/api/organizations", headers=personal_headers)
    assert personal_orgs.status_code == 200
    assert len(personal_orgs.json()) == 1
    assert personal_orgs.json()[0]["slug"] == "personal-user-1"
    login = client.post(
        "/api/auth/login",
        data={"username": "owner", "password": "password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    organization = client.post(
        "/api/organizations",
        headers=headers,
        json={"name": "Operations"},
    )
    assert organization.status_code == 201
    organization_id = organization.json()["id"]

    project = client.post(
        "/api/projects",
        headers=headers,
        json={
            "organization_id": organization_id,
            "name": "Launch",
            "description": "Release work",
        },
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    first = client.post(
        f"/api/projects/{project_id}/tasks",
        headers=headers,
        json={"title": "First"},
    )
    second = client.post(
        f"/api/projects/{project_id}/tasks",
        headers=headers,
        json={"title": "Second"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    details = client.get("/api/projects/overview/details", headers=headers)
    assert details.status_code == 200
    details_data = details.json()
    assert len(details_data["pending_tasks"]) == 2
    assert details_data["upcoming_milestones"] == []
    assert details_data["recent_activity"]
    assert details_data["pending_approvals"] == []
    assert details_data["agent_insights"] == []

    first_id = first.json()["id"]
    second_id = second.json()["id"]
    dependency = client.post(
        f"/api/tasks/{second_id}/dependencies",
        headers=headers,
        json={"depends_on_task_id": first_id},
    )
    assert dependency.status_code == 201

    cycle = client.post(
        f"/api/tasks/{first_id}/dependencies",
        headers=headers,
        json={"depends_on_task_id": second_id},
    )
    assert cycle.status_code == 409

    app.dependency_overrides.clear()
