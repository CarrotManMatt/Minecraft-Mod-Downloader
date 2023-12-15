from collections.abc import Sequence

__all__: Sequence[str] = (
    "BaseMod",
    "SimpleMod",
    "DetailedMod",
    "CustomSourceMod",
    "APISourceMod",
    "ModTag",
    "MinecraftVersionValidator",
    "UnsanitisedMinecraftVersionValidator",
    "ModLoader"
)

from collections.abc import Callable
from pathlib import Path
from typing import Final

import pathvalidate
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, URLValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from minecraft_mod_downloader.models._mem_db_core.models.utils import BaseModel
from minecraft_mod_downloader.models._mem_db_core.models.validators import (
    MinecraftVersionValidator,
    ShortIDValidator,
    TagNameValidator,
    UniqueIdentifierValidator,
    UnsanitisedMinecraftVersionValidator,
)

MAX_NAME_LENGTH: Final[int] = 65
MAX_FILE_NAME_LENGTH: Final[int] = MAX_NAME_LENGTH
MAX_VERSION_ID_LENGTH: Final[int] = 20
MAX_MOD_ID_LENGTH: Final[int] = MAX_VERSION_ID_LENGTH


assert MAX_FILE_NAME_LENGTH >= MAX_NAME_LENGTH


class ModLoader(models.TextChoices):
    """Enum of mod loader ID & display values of each mod loader."""

    FABRIC = "FA"
    QUILT = "QU"
    FORGE = "FO"


class BaseMod(BaseModel):

    @staticmethod
    def sanitise_minecraft_version(minecraft_version: str) -> str:
        try:
            MinecraftVersionValidator()(minecraft_version)
        except ValidationError:
            pass
        else:
            return minecraft_version

        e: ValidationError
        try:
            UnsanitisedMinecraftVersionValidator()(minecraft_version)
        except ValidationError as e:
            raise ValueError from e

        minecraft_version_parts: list[str] = [
            (
                version_part.lstrip("0")
                if len(version_part.lstrip("0")) > 0
                else "0"
            )
            for version_part in
            minecraft_version.split(
                ".",
                maxsplit=2
            )
        ]

        if len(minecraft_version_parts) == 2:  # noqa: PLR2004
            minecraft_version_parts.append("0")

        return ".".join(minecraft_version_parts)

    minecraft_version = models.CharField(
        f"Minecraft {_("Version")}",
        max_length=9,
        validators=[UnsanitisedMinecraftVersionValidator(), MinLengthValidator(3)],
        blank=False,
        null=False
    )
    mod_loader = models.CharField(
        _("Mod Loader"),
        max_length=2,
        choices=ModLoader.choices,
        blank=False,
        null=False
    )
    _unique_identifier = models.CharField(
        _("Unique Identifier"),
        max_length=MAX_FILE_NAME_LENGTH,
        validators=[UniqueIdentifierValidator(), MinLengthValidator(2)],
        blank=False,
        null=False
    )

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=("minecraft_version", "mod_loader", "_unique_identifier"),
                name="unique_identifier_per_environment"
            )
        ]

    def clean(self) -> None:
        if self.minecraft_version:
            self.minecraft_version = self.sanitise_minecraft_version(self.minecraft_version)

            if not (5 <= len(self.minecraft_version) <= 9):  # noqa: PLR2004
                INVALID_MINECRAFT_VERSION_MESSAGE: Final[str] = (
                    f"{_("Invalid")} Minecraft {_("version")}"
                )
                raise ValidationError(
                    {"minecraft_version": INVALID_MINECRAFT_VERSION_MESSAGE},
                    code="invalid"
                )

            e: ValidationError
            try:
                MinecraftVersionValidator()(self.minecraft_version)
            except ValidationError as e:
                raise ValidationError({"minecraft_version": e}, code="invalid") from e

        super().clean()


class SimpleMod(BaseMod):
    @property
    def identifier(self) -> str:
        return self._unique_identifier

    @identifier.setter
    def identifier(self, identifier: str) -> None:
        self._unique_identifier = identifier

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        unique_identifier_field: models.Field = self._meta.get_field("_unique_identifier")

        validator: Callable[[object], None]
        for validator in unique_identifier_field.validators:
            if isinstance(validator, UniqueIdentifierValidator):
                validator.message = "Invalid identifier"

        unique_identifier_field.verbose_name = _("Identifier")

    def __str__(self) -> str:
        return self.identifier

    class Meta:
        verbose_name = _("Simple Mod")

    @classmethod
    def get_proxy_field_names(cls) -> set[str]:
        """
        Return the set of extra names of properties that can be saved to the database.

        These are proxy fields because their values are not stored as object attributes,
        however, they can be used as a reference to a real attribute when saving objects to the
        database.
        """
        return super().get_proxy_field_names() | {"identifier"}


class ModTag(BaseModel):
    name = models.CharField(
        _("Name"),
        max_length=MAX_NAME_LENGTH,
        validators=[TagNameValidator(), MinLengthValidator(2)],
        blank=False,
        null=False,
        unique=True
    )

    class Meta:
        verbose_name = _("Mod Tag")

    def __str__(self) -> str:
        return self.name


class DetailedMod(BaseMod):
    name = models.CharField(
        _("Name"),
        max_length=MAX_NAME_LENGTH,
        validators=[MinLengthValidator(2)],
        blank=False,
        null=False,
        unique=True
    )
    version_id = models.CharField(
        _("Version ID"),
        max_length=MAX_VERSION_ID_LENGTH,
        validators=[ShortIDValidator(), MinLengthValidator(2)],
        blank=False,
        null=False,
    )
    tags = models.ManyToManyField(
        ModTag,
        verbose_name=_("Tags"),
        related_name="mods",
        blank=True
    )
    disabled = models.BooleanField(
        _("Disabled"),
        default=False
    )

    class Meta:
        # noinspection SpellCheckingInspection
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=("version_id", "name"),
                name="unique_version_id_per_name"
            ),
            models.UniqueConstraint(
                fields=("version_id", "basemod_ptr"),
                name="unique_version_id_per_unique_identifier"
            ),
            models.UniqueConstraint(
                fields=("name", "basemod_ptr"),
                name="unique_name_per_unique_identifier"
            )
        ]

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        unique_identifier_field: models.Field = self._meta.get_field("_unique_identifier")

        validator: Callable[[object], None]
        for validator in unique_identifier_field.validators:
            if isinstance(validator, UniqueIdentifierValidator):
                validator.message = "Invalid file name"

        unique_identifier_field.verbose_name = _("File Name")

    def clean(self) -> None:
        FILE_NAME_IS_VALID: Final[bool] = bool(
            self.file_name.endswith(".jar")
            and pathvalidate.is_valid_filename(self.file_name)
        )
        if not FILE_NAME_IS_VALID:
            INVALID_FILE_NAME_MESSAGE: Final[str] = _("Invalid file name")
            raise ValidationError(INVALID_FILE_NAME_MESSAGE)

        super().clean()

    def __str__(self) -> str:
        return f"{self.name} ({self.file_name})"

    @property
    def file_name(self) -> str:
        return self._unique_identifier

    @file_name.setter
    def file_name(self, file_name: str | Path) -> None:
        self._unique_identifier = (
            file_name.resolve().name if isinstance(file_name, Path) else file_name
        )


class CustomSourceMod(DetailedMod):
    download_url = models.URLField(
        _("Download URL"),
        validators=[URLValidator()],
        blank=False,
        null=False
    )

    class Meta:
        verbose_name = _("Custom Source Mod")


class APISourceMod(DetailedMod):
    class APISource(models.TextChoices):
        CURSEFORGE = "CF", "CurseForge"
        MODRINTH = "MR"

    api_source = models.CharField(
        _("API Source"),
        max_length=2,
        choices=APISource.choices,
        blank=False,
        null=False
    )
    api_mod_id = models.CharField(
        _("API Mod ID"),
        max_length=MAX_MOD_ID_LENGTH,
        validators=[ShortIDValidator(), MinLengthValidator(2)],
        blank=False,
        null=False,
    )

    class Meta:
        verbose_name = _("API Source Mod")
        # noinspection SpellCheckingInspection
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=("api_mod_id", "api_source"),
                name="unique_api_mod_id_per_api_source"
            ),
            models.UniqueConstraint(
                fields=("api_mod_id", "detailedmod_ptr"),
                name="unique_api_mod_id_per_unique_identifier"
            )
        ]
