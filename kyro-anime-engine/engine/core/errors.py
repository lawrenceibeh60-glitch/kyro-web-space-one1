"""Typed errors shared by the standalone engine modules."""


class EngineError(Exception):
    """Base class for engine failures."""


class ValidationError(EngineError):
    """Raised when input data violates a runtime invariant."""

    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = list(errors or [])


class SerializationError(EngineError):
    """Raised when data cannot be represented as valid JSON."""


class MissingResourceError(EngineError, KeyError):
    """Raised when a requested registered resource does not exist."""


class DependencyCycleError(ValidationError):
    """Raised when a dependency graph cannot be topologically ordered."""
