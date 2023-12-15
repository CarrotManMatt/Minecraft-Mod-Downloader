"""Custom exception classes that could be raised."""

from collections.abc import Sequence

__all__: Sequence[str] = (
    "BaseError",
    "ConfigSettingRequiredError",
    "ImproperlyConfiguredError",
    "ModListEntryLoadError"
)

import abc
from collections.abc import Iterable
from django.core.exceptions import ValidationError


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

        super().__init__(
            message
            if not self.environment_variable_name or message is not None
            else f"{self.environment_variable_name} has not been provided"
        )


class ModListEntryLoadError(BaseError, Exception):
    """Exception class for when a given mod-list entry could not be correctly loaded."""

    DEFAULT_MESSAGE: str = "One of the mod-list entries could not be correctly loaded."

    def __init__(self, message: str | None = None, unique_identifier: str | None = None, reason: str | ValidationError | None = None) -> None:  # noqa: E501
        """Create a new ModListEntryLoadError with the given `unique_identifier`."""
        self.unique_identifier: str | None = unique_identifier
        self.reason: str | None = (
            self.format_reason(reason) if isinstance(reason, ValidationError) else reason
        )

        super().__init__(
            message if not self.unique_identifier or message is not None else (
                f"The mod with unique identifier: \"{self.unique_identifier}\" "
                "could not be correctly loaded"
                f"{f" (Reason(s): {self.reason})" if self.reason else ""}"
            )
        )

    @staticmethod
    def format_reason(validation_error: ValidationError) -> str:
        reason: str = ""

        field_name: str
        field_errors: Iterable[str]
        for field_name, field_errors in validation_error:
            field_name = field_name.replace("_", " ").strip().replace(
                "minecraft",
                "Minecraft"
            )

            blank_is_error: bool = any(
                "cannot be blank" in field_error.lower() for field_error in field_errors
            )
            if blank_is_error:
                if reason:
                    reason += " & "
                reason += f"{field_name} cannot be blank"

            invalid_is_error: bool = bool(
                any("invalid" in field_error.lower() for field_error in field_errors)
                or any("not valid" in field_error.lower() for field_error in field_errors)
            )
            if invalid_is_error:
                if reason:
                    reason += " & "
                reason += f"{field_name} was invalid"

        return reason
