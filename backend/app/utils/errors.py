"""Domain errors raised by services. main.py turns them into JSON with a Russian message."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class ValidationFailed(DomainError):
    status_code = 422


class PermissionDenied(DomainError):
    status_code = 403


class Unauthorized(DomainError):
    status_code = 401


class Gone(DomainError):
    status_code = 410


class NotConfigured(DomainError):
    status_code = 503
