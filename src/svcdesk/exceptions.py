# ai-generated: 90% - Claude Code drafted, reviewed by the author

"""Small typed exceptions that main.py's handlers turn into the {"error": {...}} body shape."""


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class NotFound(ApiError):
    def __init__(self, message: str = "not found"):
        super().__init__(404, "not_found", message)


class Conflict(ApiError):
    def __init__(self, code: str = "invalid_transition", message: str = "invalid transition"):
        super().__init__(409, code, message)


class ValidationFailed(ApiError):
    def __init__(self, message: str = "validation error"):
        super().__init__(422, "validation", message)
