"""Exception types."""


class DataForgeError(ValueError):
    """Expected input/business error; the message is user-facing (Chinese)."""


class Cancelled(BaseException):
    """Raised when a running task is cancelled by the user.

    Derives from BaseException on purpose so a per-file ``except Exception`` in a tool
    cannot swallow cancellation. Tools must not catch BaseException, except to clean up
    temporary files/folders and then immediately re-raise (``except BaseException:
    cleanup; raise``), as ``atomic_path`` and the masking output folder do.
    """
