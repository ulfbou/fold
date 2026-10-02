class FoldError(Exception):
    exit_code = 4


class UsageError(FoldError):
    exit_code = 2


class TaskDeclarationError(FoldError):
    exit_code = 3


class SourceUnavailableError(FoldError):
    exit_code = 4
