
import os
from functools import lru_cache
import re
from guardrails import Guard
from guardrails_ai.detect_jailbreak import DetectJailbreak
from guardrails_ai.detect_pii import DetectPII


class InputBlockedError(ValueError):
    """Raised when an input fails a safety check."""


class GuardrailsUnavailableError(RuntimeError):
    """Raised when a safety check cannot run reliably."""


@lru_cache(maxsize=1)
def _jailbreak_guard() -> Guard:
    return Guard().use(
        DetectJailbreak(
            threshold=0.9,
            on_fail="noop",
        )
    )
EXPLICIT_JAILBREAK_PATTERNS = [
    r"\bignore\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above|earlier|all)\s+instructions?\b",
    r"\b(?:disregard|override)\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above|earlier)\s+instructions?\b",
    r"\b(?:reveal|show|print|display|expose|leak)\s+(?:your\s+)?(?:hidden\s+)?(?:system|developer)\s+(?:prompt|instructions?)\b",
    r"\b(?:bypass|disable|circumvent)\s+(?:the\s+)?(?:safety|security)\s+(?:rules?|filters?|guardrails?)\b",
]

@lru_cache(maxsize=1)
def _pii_guard() -> Guard:
    """Build and cache the local PII detector."""
    return Guard().use(
        DetectPII(
            pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER"],
            on_fail="fix",
        )
    )

def _has_explicit_jailbreak(message: str) -> bool:
    return any(
        re.search(pattern, message, flags=re.IGNORECASE)
        for pattern in EXPLICIT_JAILBREAK_PATTERNS
    )

def _check_jailbreak(text: str) -> bool:
    """
    Return True when the detector considers the text safe.
    Raise an error if the detector itself fails.
    """
    try:
        result = _jailbreak_guard().validate(text)
        return bool(result.validation_passed)
    except Exception as exc:
        raise GuardrailsUnavailableError(
            "The jailbreak safety check could not run."
        ) from exc



def validate_user_input(message: str) -> str:
    message = message.strip()

    if not message:
        raise InputBlockedError("Message cannot be empty.")

    if len(message) > 20_000:
        raise InputBlockedError("Message is too long.")

    # Deterministic check for recognized jailbreak patterns.
    if _has_explicit_jailbreak(message):
        raise InputBlockedError(
            "The message was blocked by PageTrail's safety checks."
        )

    # Avoid classifier false positives on very short messages.
    # The explicit checks above still run for these messages.
    if len(message.split()) >= 4 and not _check_jailbreak(message):
        raise InputBlockedError(
            "The message was blocked by PageTrail's safety checks."
        )

    return message


def contains_jailbreak(text: str) -> bool:
    """Return whether retrieved text is flagged as a possible jailbreak."""
    return not _check_jailbreak(text)


def sanitize_assistant_output(text: str) -> str:
    """
    Redact detected email addresses and phone numbers in the answer.

    Set PAGETRAIL_REDACT_PII=false to preserve these values when
    extracting contact details from user documents is intentional.
    """
    redact_pii = os.getenv("PAGETRAIL_REDACT_PII", "true").lower()

    if redact_pii in {"0", "false", "no", "off"}:
        return text

    if not text.strip():
        return text

    try:
        result = _pii_guard().validate(text)
    except Exception as exc:
        raise GuardrailsUnavailableError(
            "The output privacy check could not run."
        ) from exc

    validated = result.validated_output

    if isinstance(validated, str):
        return validated

    if result.validation_passed:
        return text

    # Never silently return unvalidated output if the validator
    # reports failure but supplies no usable result.
    raise GuardrailsUnavailableError(
        "The output could not be safely validated."
    )
