from app.core.schemas import ErrorCode


class ApiError(Exception):
    def __init__(self, status: int, code: ErrorCode, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details or []
