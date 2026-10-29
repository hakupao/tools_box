"""Exception types."""


class DataForgeError(ValueError):
    """Expected input/business error; the message is user-facing (Chinese)."""


class Cancelled(Exception):
    """Raised when a running task is cancelled by the user."""
