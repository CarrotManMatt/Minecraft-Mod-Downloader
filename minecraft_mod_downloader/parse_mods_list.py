import logging
from collections.abc import Sequence

__all__: Sequence[str] = (
    "get_default_mods_list_file_path",
    "setup_raw_mods_list",
    "load_from_mapping",
    "load_from_single_depth_iterable",
    "load_from_multi_depth_iterable",
    "load_from_str"
)

import re
import random
import os
from collections.abc import Iterable, Mapping
import json
from io import TextIOWrapper
from pathlib import Path
from typing import Final, Any

from django.core.exceptions import ValidationError

from minecraft_mod_downloader import config
from minecraft_mod_downloader.config import FALSE_VALUES, TRUE_VALUES, settings
from minecraft_mod_downloader.exceptions import ConfigSettingRequiredError, ImproperlyConfiguredError, ModListEntryLoadError
from minecraft_mod_downloader.models import APISourceMod, ModLoader, SimpleMod, UnsanitisedMinecraftVersionValidator, CustomSourceMod, DetailedMod


def get_default_mods_list_file_path() -> Path:
    file_type: str
    for file_type in ("", "json", "csv", "txt"):
        cased_file_types: Iterable[str] = {file_type.title(), file_type, file_type.upper()}
        cased_file_type: str
        for cased_file_type in cased_file_types:
            cased_mod: str
            for cased_mod in ("mod", "Mod", "MOD", "mods", "Mods", "MODS"):
                mods_list_file_path: Path = Path(f"{cased_mod}.{cased_file_type}")
                if mods_list_file_path.is_file():
                    return mods_list_file_path

                seperator: str
                for seperator in ("-", "_"):
                    cased_list: str
                    for cased_list in ("list", "List", "LIST"):
                        mods_list_file_path = Path(
                            f"{cased_mod}{seperator}{cased_list}.{cased_file_type}"
                        )
                        if mods_list_file_path.is_file():
                            return mods_list_file_path

    raise ConfigSettingRequiredError(environment_variable_name="MODS_LIST_FILE")


def get_minecraft_version_from_filename(filename: str) -> str | None:
    minecraft_version_regex: re.Match[str] | None = re.match(
        f"{r"\A"}.*(?P<minecraft_version>{UnsanitisedMinecraftVersionValidator.UNSANITISED_MINECRAFT_VERSION_RE.strip(r"\AZ")}).*{r"\Z"}",
        filename
    )

    if minecraft_version_regex is None:
        return None

    return minecraft_version_regex.group("minecraft_version")


def setup_raw_mods_list(*, mods_list_file: TextIOWrapper | None, mods_list: str | None, force_env_variables: bool = False) -> None:  # noqa: E501
    file_name_minecraft_version: str | None = None
    file_name_mod_loader: ModLoader | None = None
    if mods_list is not None or mods_list_file is not None:
        file_path: Path
        for file_path in Path().iterdir():
            temp_file_name_minecraft_version: str | None = get_minecraft_version_from_filename(
                file_path.name
            )
            file_name_minecraft_version_is_empty: bool = bool(
                temp_file_name_minecraft_version is not None
                and file_name_minecraft_version is None
            )
            if file_name_minecraft_version_is_empty:
                file_name_minecraft_version = temp_file_name_minecraft_version

            temp_file_name_mod_loader: ModLoader | None = config.get_mod_loader_from_filename(
                file_path.name
            )
            file_name_mod_loader_is_empty: bool = bool(
                temp_file_name_mod_loader is not None
                and file_name_mod_loader is None
            )
            if file_name_mod_loader_is_empty:
                file_name_mod_loader = temp_file_name_mod_loader

    if mods_list is None or force_env_variables:
        if mods_list_file is None or force_env_variables:
            raw_mods_list_file_path: str = os.getenv("MODS_LIST_FILE_PATH", "")
            mods_list_file_path: Path = (
                Path(raw_mods_list_file_path)
                if raw_mods_list_file_path or force_env_variables
                else get_default_mods_list_file_path()
            )

            if not mods_list_file_path.is_file():
                INVALID_MODS_LIST_FILE_PATH_MESSAGE: Final[str] = (
                    "MODS_LIST_FILE_PATH must be a valid path to your mods-list file"
                )
                raise ImproperlyConfiguredError(INVALID_MODS_LIST_FILE_PATH_MESSAGE)

            with mods_list_file_path.open("r") as mods_list_file:
                mods_list = mods_list_file.read()

            file_name_minecraft_version = get_minecraft_version_from_filename(
                mods_list_file_path.name
            )

        else:
            mods_list = mods_list_file.read()

    load_from_str(
        mods_list,
        known_minecraft_version=file_name_minecraft_version,
        known_mod_loader=file_name_mod_loader
    )


def load_from_mapping(raw_mods_list_dict: Mapping[str, Any]) -> None:
    raise NotImplementedError()  # TODO


def load_from_single_depth_iterable(raw_mods_list_iterable: Iterable[str], *, known_minecraft_version: str | None = None, known_mod_loader: ModLoader | None = None) -> None:
    raw_identifier: str
    for raw_identifier in raw_mods_list_iterable:
        if not raw_identifier:
            continue

        try:
            created_mod: SimpleMod
            mod_was_created: bool
            created_mod, mod_was_created = SimpleMod.objects.get_or_create(
                _unique_identifier=raw_identifier.strip(", \n\t"),
                minecraft_version=(
                    known_minecraft_version
                    if known_minecraft_version
                    else settings["FILTER_MINECRAFT_VERSION"]
                ),
                mod_loader=(
                    known_mod_loader
                    if known_mod_loader
                    else settings["FILTER_MOD_LOADER"]
                )
            )
        except ValidationError as e:
            raise ModListEntryLoadError(
                unique_identifier=raw_identifier,
                reason=e
            ) from None

        if mod_was_created:
            logging.debug(f"Successfully created mod object: {created_mod!r}")
        else:
            logging.debug(f"Retrieved {created_mod!r} (already existed)")


def _load_single_mod_from_partial_collection(raw_mod_details_collection: list[str], *, download_source: APISourceMod.APISource | str, known_minecraft_version: str | None = None, known_mod_loader: ModLoader | None = None) -> tuple[DetailedMod, bool]:  # noqa: E501
    instance_defaults: dict[str, object] = {
        "name": raw_mod_details_collection[0].strip(),
        "version_id": raw_mod_details_collection[2].strip()
    }

    disabled_value_needs_error_showing: bool = False

    ModClass: type[DetailedMod]
    if isinstance(download_source, APISourceMod.APISource):
        ModClass = APISourceMod
        instance_defaults.update(
            {
                "api_source": download_source,
                "api_mod_id": raw_mod_details_collection[3].strip()
            }
        )
        if len(raw_mod_details_collection) > 4:
            if raw_mod_details_collection[4].strip() not in TRUE_VALUES | FALSE_VALUES:
                disabled_value_needs_error_showing = True
            else:
                instance_defaults["disabled"] = (
                    raw_mod_details_collection[4].strip() in TRUE_VALUES
                )
    else:
        ModClass = CustomSourceMod
        instance_defaults["download_url"] = download_source
        if len(raw_mod_details_collection) > 3:
            if raw_mod_details_collection[3].strip() not in TRUE_VALUES | FALSE_VALUES:
                disabled_value_needs_error_showing = True
            else:
                instance_defaults["disabled"] = (
                    raw_mod_details_collection[3].strip() in TRUE_VALUES
                )

    if disabled_value_needs_error_showing:
        raise ValueError(f"Invalid value for {"disabled"!r} flag, must be a boolean value")

    e: ValidationError
    try:
        return ModClass.objects.get_or_create(
            minecraft_version=(
                known_minecraft_version
                if known_minecraft_version
                else settings["FILTER_MINECRAFT_VERSION"]
            ),
            mod_loader=(
                known_mod_loader
                if known_mod_loader
                else settings["FILTER_MOD_LOADER"]
            ),
            _unique_identifier=raw_mod_details_collection[1].strip(),
            defaults=instance_defaults
        )
    except ValidationError as e:
        raise ModListEntryLoadError(
            unique_identifier=raw_mod_details_collection[1].strip(),
            reason=e
        ) from None


def load_from_multi_depth_iterable(raw_mods_list_iterable: Iterable[str], *, known_minecraft_version: str | None = None, known_mod_loader: ModLoader | None = None) -> None:
    raw_mod_details: str
    for raw_mod_details in raw_mods_list_iterable:
        raw_mod_details = raw_mod_details.strip(", \n\t").replace("'", "\"")

        raw_mod_details_collection: list[str]
        raw_tags: str
        if raw_mod_details.count("\"") == 0:
            raw_mod_details_collection = raw_mod_details.split(",")
            raw_tags = raw_mod_details_collection.pop(3)

        elif raw_mod_details.count("\"") == 2:
            escaped_raw_mod_details: list[str] = raw_mod_details.split("\"", maxsplit=2)
            raw_tags = escaped_raw_mod_details[1].strip(",")

            speech_marks_usage_is_correct: bool = bool(
                escaped_raw_mod_details[0].endswith(",")
                and escaped_raw_mod_details[2].startswith(",")
            )
            if not speech_marks_usage_is_correct:
                raise ValueError("Incorrect usage of speech marks in mods-list")

            raw_mod_details_collection = (
                escaped_raw_mod_details[0].split(",")
                + escaped_raw_mod_details[2].split(",")
            )

        else:
            raise ValueError("Incorrect usage of speech marks in mods-list")

        if len(raw_mod_details_collection) > 6:
            raise ValueError("Too many values supplied for a single mod's details")

        created_mod: DetailedMod
        mod_was_created: bool

        api_source_is_curseforge: bool = bool(
            "curse" in raw_mod_details_collection[3].lower()
            or "forge" in raw_mod_details_collection[3].lower()
        )
        if api_source_is_curseforge:
            raw_mod_details_collection.pop(3)
            created_mod, mod_was_created = _load_single_mod_from_partial_collection(
                raw_mod_details_collection,
                download_source=APISourceMod.APISource.CURSEFORGE,
                known_minecraft_version=known_minecraft_version,
                known_mod_loader=known_mod_loader
            )

        elif "modrinth" in raw_mod_details_collection[3].lower():
            raw_mod_details_collection.pop(3)
            created_mod, mod_was_created = _load_single_mod_from_partial_collection(
                raw_mod_details_collection,
                download_source=APISourceMod.APISource.MODRINTH,
                known_minecraft_version=known_minecraft_version,
                known_mod_loader=known_mod_loader
            )

        else:
            download_url: str = raw_mod_details_collection.pop(3)
            created_mod, mod_was_created = _load_single_mod_from_partial_collection(
                raw_mod_details_collection,
                download_source=download_url,
                known_minecraft_version=known_minecraft_version,
                known_mod_loader=known_mod_loader
            )

        # TODO add tags to `created_mod`

        if mod_was_created:
            logging.debug(f"Successfully created mod object: {created_mod!r}")
        else:
            logging.debug(f"Retrieved {created_mod!r} (already existed)")


def load_from_str(raw_mods_list: str, *, known_minecraft_version: str | None = None, known_mod_loader: ModLoader | None = None) -> None:
    try:
        raw_mods_list_mapping: Mapping[str, Any] = json.loads(raw_mods_list)
    except json.JSONDecodeError:
        pass
    else:
        load_from_mapping(raw_mods_list_mapping)

    raw_mods_list_collection: Sequence[str] = raw_mods_list.splitlines()

    if len(raw_mods_list_collection) == 0:
        EMPTY_MODS_LIST_ERROR: Final[str] = "Empty mods list."
        raise ValueError(EMPTY_MODS_LIST_ERROR)

    if len(raw_mods_list_collection) == 1:
        load_from_single_depth_iterable(
            raw_mods_list.strip("\n").split(","),
            known_minecraft_version=known_minecraft_version,
            known_mod_loader=known_mod_loader
        )

    else:
        IS_SINGLE_DEPTH: Final[bool] = all(
            "," not in raw_identifier.strip(", \t\n")
            for raw_identifier
            in random.sample(raw_mods_list_collection, len(raw_mods_list_collection) // 2)
        )
        if IS_SINGLE_DEPTH:
            load_from_single_depth_iterable(
                raw_mods_list_collection,
                known_minecraft_version=known_minecraft_version,
                known_mod_loader=known_mod_loader
            )
        else:
            load_from_multi_depth_iterable(
                raw_mods_list_collection,
                known_minecraft_version=known_minecraft_version,
                known_mod_loader=known_mod_loader
            )
