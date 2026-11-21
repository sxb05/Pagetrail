import os

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.base import Base
from app.db import models as _models  # noqa: F401
from app.services.rag import rag_documents


def test_all_sqlalchemy_application_tables_are_registered():
    expected = {
        "users",
        "conversations",
        "chat_messages",
        "long_term_memory",
        "organizations",
        "organization_members",
        "projects",
        "project_members",
        "tasks",
        "milestones",
        "task_dependencies",
        "project_documents",
        "meeting_notes",
        "agent_runs",
        "agent_approvals",
        "agent_events",
        "agent_artifacts",
        "agent_schedules",
        "integration_connections",
        "audit_logs",
    }
    assert expected.issubset(set(Base.metadata.tables))
    task_table = Base.metadata.tables["tasks"]
    assert any(
        constraint.name == "uq_tasks_id_project"
        for constraint in task_table.constraints
    )


def test_alembic_chain_has_one_head_and_rag_table_is_known():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    config = Config(os.path.join(repo_root, "backend", "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()
    assert heads == ["002_project_operations"]
    assert rag_documents.name == "rag_documents"
    assert Base.metadata.tables["task_dependencies"].constraints
