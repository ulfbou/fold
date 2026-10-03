"""Fold exception hierarchy and CLI exit-code mapping."""


class FoldError(Exception):
    """Base class for expected Fold failures."""

    exit_code = 4


class UsageError(FoldError):
    """Invalid command-line usage."""

    exit_code = 2


class UnknownFieldError(UsageError):
    """A user requested a field that is not present."""


class TaskDeclarationError(FoldError):
    """The task artifact is missing, unsafe, or invalid."""

    exit_code = 3


class SourceUnavailableError(FoldError):
    """An authoritative source is unavailable or invalid."""

    exit_code = 4


class InvariantError(FoldError):
    """The evaluated graph or envelope violates an internal invariant."""

    exit_code = 5
