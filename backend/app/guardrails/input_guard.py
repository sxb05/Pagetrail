
MAX_MESSAGE_LENGTH = 12_000


class InputGuardError(ValueError):
    """Raised when a user message violates input policy."""


def validate_user_message(message: str) -> str:
    if not isinstance(message, str):
        raise InputGuardError("Message must be text.")

    message = message.strip()

    if not message:
        raise InputGuardError("Message cannot be empty.")

    if len(message) > MAX_MESSAGE_LENGTH:
        raise InputGuardError("Message exceeds the allowed length.")

    return message
