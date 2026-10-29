"""Exception types."""


class DataForgeError(ValueError):
    """Expected input/business error; the message is user-facing (Chinese)."""


class Cancelled(BaseException):
    """Raised when a running task is cancelled by the user.

    Derives from BaseException on purpose so a per-file ``except Exception`` in a tool
    cannot swallow cancellation. Tools must never catch BaseException.
    """
