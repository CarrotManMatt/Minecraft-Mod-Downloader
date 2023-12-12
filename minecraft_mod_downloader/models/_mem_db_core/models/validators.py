"""Validators in _mem_db_core app."""

from collections.abc import Sequence

__all__: Sequence[str] = (
    "UniqueIdentifierValidator",
    "MinecraftVersionValidator",
    "UnsanitisedMinecraftVersionValidator",
    "ShortIDValidator",
    "TagNameValidator"
)

import re
from django.core.validators import RegexValidator
from django.utils import deconstruct
from django.utils.translation import gettext_lazy as _

# NOTE: Adding external package functions to the global scope for frequent usage
deconstructible = deconstruct.deconstructible


@deconstructible
class UniqueIdentifierValidator(RegexValidator):
    """Validator, which ensures a given identifier matches the given regex."""

    UNIQUE_IDENTIFIER_RE: str = r"\A[A-Za-z](?:[A-Za-z0-9 .\-_]*[A-Za-z0-9])?\Z"

    message: str = _("Invalid unique identifier")
    regex: re.Pattern[str] = re.compile(UNIQUE_IDENTIFIER_RE)


@deconstructible
class MinecraftVersionValidator(RegexValidator):
    """Validator, which ensures a given minecraft_version string is valid."""

    MINECRAFT_VERSION_RE: str = r"\A1\.[1-9]\d{0,2}\.(?:0|[1-9]\d?)\Z"

    message: str = f"""{_("Invalid")} Minecraft {_("version")}"""
    regex: re.Pattern[str] = re.compile(MINECRAFT_VERSION_RE)


@deconstructible
class UnsanitisedMinecraftVersionValidator(RegexValidator):
    """Validator, which ensures a given unsanitised minecraft_version string can be fixed."""

    UNSANITISED_MINECRAFT_VERSION_RE: str = r"\A0*1\.0*[1-9]\d{0,2}(?:\.0*(?:0|[1-9]\d?))?\Z"

    message: str = f"""{_("Invalid unsanitised")} Minecraft {_("version")}"""
    regex: re.Pattern[str] = re.compile(UNSANITISED_MINECRAFT_VERSION_RE)


@deconstructible
class ShortIDValidator(RegexValidator):
    SHORT_ID_RE: str = r"\A[A-Za-z0-9]+\Z"

    message: str = _("Invalid short ID")
    regex: re.Pattern[str] = re.compile(SHORT_ID_RE)


@deconstructible
class TagNameValidator(RegexValidator):
    TAG_NAME_RE: str = r"\A[a-z]{2,}\Z"

    message: str = _("Invalid name")
    regex: re.Pattern[str] = re.compile(TAG_NAME_RE)
