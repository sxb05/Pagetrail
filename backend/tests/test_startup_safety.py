import os
import subprocess
import sys
from pathlib import Path


def test_guardrails_module_does_not_import_ml_detectors_when_disabled():
    env = os.environ.copy()
    env["PAGETRAIL_GUARDRAILS"] = "false"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    env["JWT_SECRET_KEY"] = "test-only-jwt-secret-key-at-least-32-characters"

    code = (
        "import sys; "
        "from app.services import guardrails; "
        "assert 'guardrails' not in sys.modules; "
        "assert 'guardrails_ai.detect_jailbreak' not in sys.modules; "
        "assert 'guardrails_ai.detect_pii' not in sys.modules; "
        "assert guardrails.validate_user_input('Hello there, summarize this')"
        " == 'Hello there, summarize this'"
    )

    subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        env=env,
        cwd=Path(__file__).resolve().parents[2],
        timeout=20,
    )


def test_legacy_initializer_refuses_without_explicit_local_permission():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    env.pop("PAGETRAIL_ALLOW_LEGACY_INIT", None)
    env.pop("ALEMBIC_DATABASE_URL", None)
    code = (
        "from app.db.session import init_db\n"
        "try:\n"
        "    init_db()\n"
        "except RuntimeError as exc:\n"
        "    assert 'PAGETRAIL_ALLOW_LEGACY_INIT=true' in str(exc)\n"
        "else:\n"
        "    raise AssertionError('legacy initializer was not blocked')\n"
    )
    subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        env=env,
        cwd=Path(__file__).resolve().parents[2],
        timeout=20,
    )



def test_liveness_and_readiness_are_separate_without_database_config():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    for name in (
        "DATABASE_URL",
        "DATABASE_ADMIN_URL",
        "DATABASE_HOST",
        "DATABASE_NAME",
        "DATABASE_USERNAME",
        "DATABASE_PASSWORD",
    ):
        env.pop(name, None)
        env[name] = ""

    code = (
        "from fastapi.testclient import TestClient; "
        "from app.main import app; "
        "client = TestClient(app); "
        "assert client.get('/health/live').status_code == 200; "
        "assert client.get('/api/health').status_code == 200; "
        "assert client.get('/health/ready').status_code == 503"
    )

    subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        env=env,
        cwd=Path(__file__).resolve().parents[2],
        timeout=30,
    )
