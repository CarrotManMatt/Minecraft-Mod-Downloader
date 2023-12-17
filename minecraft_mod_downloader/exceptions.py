"""Custom exception classes that could be raised."""
import re
from collections.abc import Sequence

__all__: Sequence[str] = (
    "BaseError",
    "ConfigSettingRequiredError",
    "ImproperlyConfiguredError",
    "ModListEntryLoadError",
    "ModTagLoadError",
    "ModRequiresManualDownloadError",
    "NoCompatibleModVersionFoundOnlineError",
    "InvalidCalculatedFileHash"
)

import abc
from collections.abc import Iterable
from typing import Final, TYPE_CHECKING

from django.core.exceptions import ValidationError

if TYPE_CHECKING:
    from hashlib import _Hash as HashType
    from minecraft_mod_downloader.models import APISourceMod, CustomSourceMod


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

        if set(self.__dict__.keys()) - {"message"}:
            formatted += f" ({
                ", ".join(
                    {
                        f"{key}={value!r}"
                        for key, value
                        in self.__dict__.items()
                        if key != "message"
                    }
                )
            })"

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


class ModTagLoadError(ModListEntryLoadError):
    """Exception class for when a given mod-tag could not be correctly loaded."""

    DEFAULT_MESSAGE: str = "One of the mod-tag entries could not be correctly loaded."

    def __init__(self, message: str | None = None, name: str | None = None, mod_unique_identifier: str | None = None, reason: str | ValidationError | None = None) -> None:  # noqa: E501
        """
        Create a new ModTagLoadError with the given `name`.

        The mod's `unique_identifier` that this tag is associated can also be given.
        """
        self.name: str | None = name
        self.reason: str | None = (
            self.format_reason(reason) if isinstance(reason, ValidationError) else reason
        )

        super().__init__(
            message,
            mod_unique_identifier,
            self.reason if "tag" in self.reason else f"tag was invalid: {self.reason}"
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
                reason += f"tag {field_name} cannot be blank"

            invalid_is_error: bool = bool(
                any("invalid" in field_error.lower() for field_error in field_errors)
                or any("not valid" in field_error.lower() for field_error in field_errors)
            )
            if invalid_is_error:
                if reason:
                    reason += " & "
                reason += f"tag {field_name} was invalid"

        return reason


class NoCompatibleModVersionFoundOnlineError(BaseError, RuntimeError):
    DEFAULT_MESSAGE: str = "No compatible mod version can be found online."

    def __init__(self, message: str | None = None, mod: "APISourceMod | None" = None) -> None:  # noqa: E501
        """Create a new NoCompatibleModVersionFoundOnlineError with the given `mod`."""
        self.mod: APISourceMod | None = mod

        super().__init__(
            message
            if message is not None
            else (
                f"{self.DEFAULT_MESSAGE.strip(".")} for mod: {self.mod}, "
                f"on {self.mod.get_api_source_display()} API."
            )
        )


class ModRequiresManualDownloadError(BaseError, RuntimeError):
    DEFAULT_MESSAGE: str = "Mods from custom sources must be downloaded manually."

    def __init__(self, message: str | None = None, mod: "CustomSourceMod | None" = None) -> None:  # noqa: E501
        """Create a new ModRequiresManualDownloadError with the given `mod`."""
        self.mod: CustomSourceMod | None = mod

        super().__init__(
            message
            if message is not None
            else (
                f"{self.DEFAULT_MESSAGE}. "
                f"Download the latest version of {self.mod} from {self.mod.download_url}. "
                f"(Current mod version: {mod.version_id}.)"
            )
        )


class InvalidCalculatedFileHash(BaseError, ValueError):
    DEFAULT_MESSAGE: str = (
        "Hash of downloaded mod file did not match given hash from latest-version lookup."
    )

    def __init__(self, message: str | None = None, expected_hash: str | Iterable[str] | None = None, calculated_hash: str | None = None) -> None:  # noqa: E501
        """Create a new ModRequiresManualDownloadError with the given `mod`."""
        INVALID_EXPECTED_HASH_MESSAGE: Final[str] = (
            f"Argument {expected_hash=} must be a valid hash-hex-digest"
        )
        if isinstance(expected_hash, str):
            if not re.match(r"\A[0-9A-Fa-f]+\Z", expected_hash):
                raise ValueError(INVALID_EXPECTED_HASH_MESSAGE)
        if isinstance(expected_hash, Iterable):
            inner_expected_hash: str
            for inner_expected_hash in expected_hash:
                if not re.match(r"\A[0-9A-Fa-f]+\Z", inner_expected_hash):
                    raise ValueError(INVALID_EXPECTED_HASH_MESSAGE)
        self.expected_hash: str | Iterable[str] | None = expected_hash

        if calculated_hash is not None:
            INVALID_CALCULATED_HASH_MESSAGE: Final[str] = (
                f"Argument {calculated_hash=} must be a valid hash-hex-digest"
            )
            if not re.match(r"\A[0-9A-Fa-f]+\Z", calculated_hash):
                raise ValueError(INVALID_CALCULATED_HASH_MESSAGE)
        self.calculated_hash: str | None = calculated_hash

        super().__init__(message)

    def __str__(self) -> str:
        return repr(self)
