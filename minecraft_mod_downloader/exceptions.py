"""Custom exception classes that could be raised."""

import abc
from collections.abc import Sequence

__all__: Sequence[str] = (
    "BaseError",
    "ConfigSettingRequiredError",
    "ImproperlyConfiguredError"
)


class BaseError(BaseException, abc.ABC):
    """Base exception parent class."""

    DEFAULT_MESSAGE: str

    def __init__(self, message: str | None = None) -> None:
        """Initialize a new exception with the given error message."""
        self.message: str = message or self.DEFAULT_MESSAGE

        super().__init__(self.message)

    def __repr__(self) -> str:
        """Generate a developer-focused representation of the exception's attributes."""
        formatted: str = self.message

        attributes: set[str] = set(self.__dict__.keys())
        attributes.discard("message")
        if attributes:
            formatted += f" ({", ".join({f"{attribute=}" for attribute in attributes})})"

        return formatted


class ImproperlyConfiguredError(BaseError, Exception):
    """Exception class to raise when the environment variables are not correctly provided."""

    DEFAULT_MESSAGE: str = "Environment variables have not been correctly provided."


class ConfigSettingRequiredError(ImproperlyConfiguredError):
    """Exception class for when a given environment variables is required but not provided."""

    DEFAULT_MESSAGE: str = (
        "One of the environment variables was not provided, but is required."
    )

    def __init__(self, message: str | None = None, environment_variable_name: str | None = None) -> None:  # noqa: E501
        """Create a new ConfigSettingRequiredError with the given environment variable name."""
        self.environment_variable_name: str | None = environment_variable_name

        super().__init__(message)
