from collections.abc import Sequence

__all__: Sequence[str] = (
    "MAX_NAME_LENGTH",
    "MAX_FILE_NAME_LENGTH",
    "MAX_VERSION_ID_LENGTH",
    "MAX_MOD_ID_LENGTH",
    "ModLoader",
    "BaseMod",
    "SimpleMod",
    "DetailedMod",
    "CustomMod",
    "APIMod"
)

import abc
import re
from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Final, Self

import pathvalidate
import validators

MAX_NAME_LENGTH: Final[int] = 30
MAX_FILE_NAME_LENGTH: Final[int] = MAX_NAME_LENGTH
MAX_VERSION_ID_LENGTH: Final[int] = 8
MAX_MOD_ID_LENGTH: Final[int] = MAX_VERSION_ID_LENGTH


assert MAX_FILE_NAME_LENGTH >= MAX_NAME_LENGTH


class ModLoader(Enum):
    FORGE = "Forge"
    FABRIC = "Fabric"
    QUILT = "Fabric"


class BaseMod(abc.ABC):
    @staticmethod
    def identifier_is_valid(identifier: str) -> bool:
        return bool(
            re.match(r"\A[A-Za-z](?:[A-Za-z0-9 .\-_]*[A-Za-z0-9])?\Z", identifier)
        )

    @staticmethod
    def sanitise_minecraft_version(minecraft_version: str) -> str:
        minecraft_version_is_sanitised: bool = bool(
            re.match(
                r"\A1\.[1-9]\d{0,2}\.(?:0|[1-9]\d{0,1})\Z",
                minecraft_version
            )
        )
        if minecraft_version_is_sanitised:
            return minecraft_version

        minecraft_version_needs_sanitising: bool = bool(
            re.match(
                r"\A0*1\.0*[1-9]\d{0,2}(?:\.0*(?:0|[1-9]\d{0,1}))?\Z",
                minecraft_version
            )
        )
        if minecraft_version_needs_sanitising:
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

            if len(minecraft_version_parts) == 2:
                minecraft_version_parts.append("0")

            return ".".join(minecraft_version_parts)

        raise ValueError(f"Invalid minecraft_version: {minecraft_version!r}")

    def __init__(self, minecraft_version: str, mod_loader: str | ModLoader) -> None:
        self._minecraft_version: str = self.sanitise_minecraft_version(minecraft_version)

        self._mod_loader: ModLoader = (
            mod_loader
            if isinstance(mod_loader, ModLoader)
            else ModLoader(mod_loader)
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, type(self)):
            return other.get_unique_identifier() == self.get_unique_identifier()

        return NotImplemented

    def __str__(self) -> str:
        return self.get_unique_identifier()

    @property
    def minecraft_version(self) -> str:
        return self._minecraft_version

    @property
    def mod_loader(self) -> ModLoader:
        return self._mod_loader

    @abc.abstractmethod
    def get_unique_identifier(self) -> str:
        """"""


class SimpleMod(BaseMod):
    def __init__(self, minecraft_version: str, mod_loader: str | ModLoader, identifier: str) -> None:  # noqa: E501
        if not self.identifier_is_valid(identifier) or len(identifier) > MAX_FILE_NAME_LENGTH:
            raise ValueError(f"Invalid identifier: {identifier!r}")
        self._identifier: str = identifier

        super().__init__(minecraft_version, mod_loader)

    def get_unique_identifier(self) -> str:
        return self._minecraft_version + self._mod_loader.value + self._identifier

    @property
    def identifier(self) -> str:
        return self._identifier

    def __str__(self) -> str:
        return self.identifier


class DetailedMod(BaseMod):
    @staticmethod
    def id_is_valid(id_to_check: str) -> bool:
        return bool(re.match(r"\A[A-Za-z0-9]+\Z", id_to_check))

    def __init__(self, minecraft_version: str, mod_loader: str | ModLoader, name: str, file_name: str | Path, version_id: str, tags: Iterable[str], disabled: bool) -> None:  # noqa: E501
        if not self.identifier_is_valid(name) or len(name) > MAX_NAME_LENGTH:
            raise ValueError(f"Invalid name: {name!r}")
        self.name: str = name

        file_name = file_name if isinstance(file_name, str) else file_name.resolve().name
        file_name_is_valid: bool = bool(
            file_name.endswith(".jar")
            and pathvalidate.is_valid_filename(file_name)
            and len(file_name) <= MAX_FILE_NAME_LENGTH
        )
        if not file_name_is_valid:
            raise ValueError(f"Invalid file_name: {file_name!r}")
        self._file_name: str = file_name

        if not self.id_is_valid(version_id) or len(version_id) > MAX_VERSION_ID_LENGTH:
            raise ValueError(f"Invalid version_id: {version_id!r}")
        self.version_id: str = version_id

        tags_set: set[str] = set(tags)
        if any(not re.match(r"\A[a-z]{2,}\Z", tag) for tag in tags_set):
            raise ValueError(f"One or more invalid tags: {tags!r}")
        self.tags: set[str] = tags_set

        self.disabled: bool = disabled

        super().__init__(minecraft_version, mod_loader)

    def get_unique_identifier(self) -> str:
        return self._minecraft_version + self._mod_loader.value + self._file_name

    @property
    def file_name(self) -> str:
        return self._file_name

    def __str__(self) -> str:
        return self.name


class CustomMod(DetailedMod):
    def __init__(self, minecraft_version: str, mod_loader: str | ModLoader, name: str, file_name: str | Path, version_id: str, tags: Iterable[str], disabled: bool, url: str) -> None:  # noqa: E501
        e: validators.ValidationError
        try:
            validators.url(url)
        except validators.ValidationError:
            raise ValueError(f"Invalid url: {url!r}") from None

        super().__init__(
            minecraft_version,
            mod_loader,
            name,
            file_name,
            version_id,
            tags,
            disabled
        )


class APIMod(DetailedMod, abc.ABC):
    def __init__(self, minecraft_version: str, mod_loader: str | ModLoader, name: str, file_name: str | Path, version_id: str, tags: Iterable[str], disabled: bool, mod_id: str) -> None:  # noqa: E501
        if not self.id_is_valid(mod_id) or len(mod_id) > MAX_MOD_ID_LENGTH:
            raise ValueError(f"Invalid mod_id: {mod_id!r}")
        self.mod_id: str = mod_id

        super().__init__(
            minecraft_version,
            mod_loader,
            name,
            file_name,
            version_id,
            tags,
            disabled
        )


class ModrinthMod(APIMod):
    """"""


class CurseForgeMod(APIMod):
    """"""
