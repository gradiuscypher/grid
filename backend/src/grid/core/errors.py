class GridError(Exception):
    """Base for service-layer errors that routers translate to HTTP responses."""


class NotFoundError(GridError):
    pass


class ForbiddenError(GridError):
    pass


class UnauthorizedError(GridError):
    pass


class ConflictError(GridError):
    pass


class ValidationError(GridError):
    pass
