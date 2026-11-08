
from types import SimpleNamespace

import pytest

from app.services import guardrails as service


def test_safe_message_is_accepted(monkeypatch):
    monkeypatch.setattr(
        service, "_check_jailbreak", lambda text: True
    )

    result = service.validate_user_input(
        "Summarize my uploaded document."
    )

    assert result == "Summarize my uploaded document."


def test_flagged_message_is_rejected(monkeypatch):
    """The ML jailbreak classifier blocks a flagged message.

    Skipped when PAGETRAIL_GUARDRAILS=false because the ML check is
    intentionally bypassed in that mode — regex checks still run.
    """
    if not service._ML_ENABLED:
        pytest.skip("PAGETRAIL_GUARDRAILS=false: ML classifier is disabled.")

    monkeypatch.setattr(
        service, "_check_jailbreak", lambda text: False
    )

    with pytest.raises(service.InputBlockedError):
        service.validate_user_input(
            "A test message flagged by the safety detector"
        )


def test_empty_message_is_rejected():
    with pytest.raises(service.InputBlockedError):
        service.validate_user_input("   ")


def test_output_uses_validated_text(monkeypatch):
    """The PII guard replaces detected addresses in assistant output.

    Skipped when PAGETRAIL_GUARDRAILS=false because
    sanitize_assistant_output returns input unmodified in that mode.
    """
    if not service._ML_ENABLED:
        pytest.skip("PAGETRAIL_GUARDRAILS=false: PII guard is disabled.")

    monkeypatch.setenv("PAGETRAIL_REDACT_PII", "true")

    fake_result = SimpleNamespace(
        validation_passed=False,
        validated_output="Contact: [EMAIL_ADDRESS]",
    )
    fake_guard = SimpleNamespace(
        validate=lambda text: fake_result
    )

    monkeypatch.setattr(
        service, "_pii_guard", lambda: fake_guard
    )

    result = service.sanitize_assistant_output(
        "Contact: person@example.com"
    )

    assert result == "Contact: [EMAIL_ADDRESS]"


def test_pii_redaction_can_be_disabled(monkeypatch):
    monkeypatch.setenv("PAGETRAIL_REDACT_PII", "false")

    original = "Contact: person@example.com"

    assert service.sanitize_assistant_output(original) == original
