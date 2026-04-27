"""Project-specific exceptions."""


class PerfRunnerError(RuntimeError):
    """Base error for perf runner failures."""


class PerfNotInstalledError(PerfRunnerError):
    """Raised when the perf executable is not available."""


class PerfPermissionError(PerfRunnerError):
    """Raised when perf cannot run because of permissions."""


class PerfTimeoutError(PerfRunnerError):
    """Raised when perf does not finish before the timeout."""
