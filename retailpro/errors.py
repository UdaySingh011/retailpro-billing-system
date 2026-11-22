"""Custom exception hierarchy: every expected failure derives from AppError."""


class AppError(Exception):
    """Base class for all user-facing errors."""


class ValidationError(AppError):
    pass


class NotFoundError(AppError):
    pass


class DuplicateError(AppError):
    pass


class StockError(AppError):
    pass
