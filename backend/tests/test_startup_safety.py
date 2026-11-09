import os
import subprocess
import sys
from pathlib import Path


def test_guardrails_module_does_not_import_ml_detectors_when_disabled():
    env = os.environ.copy()
    env["PAGETRAIL_GUARDRAILS"] = "false"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])

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
