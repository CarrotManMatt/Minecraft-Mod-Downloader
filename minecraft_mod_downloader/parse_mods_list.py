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
from collections.abc import Iterator, Iterable, Mapping
import json
from io import TextIOWrapper
from pathlib import Path
from typing import Collection, Final, TypeAlias
import logging

from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.serializers.base import DeserializedObject

from minecraft_mod_downloader import config
from minecraft_mod_downloader.config import FALSE_VALUES, TRUE_VALUES, settings
from minecraft_mod_downloader.exceptions import ConfigSettingRequiredError, ImproperlyConfiguredError, ModListEntryLoadError, ModTagLoadError
from minecraft_mod_downloader.models import APISourceMod, ModLoader, ModTag, SimpleMod, UnsanitisedMinecraftVersionValidator, CustomSourceMod, DetailedMod


JsonOutput: TypeAlias = dict[str, object] | float | int | str | list[object] | bool | None

EMPTY_MODS_LIST_MESSAGE: Final[str] = "Empty mods list."
INVALID_MODS_LIST_MAPPING_MESSAGE: Final[str] = (
    "Mods-list could not be parsed: empty/invalid input"
)
REQUIRED_DETAILED_MOD_KEYS: Iterable[str] = (
    "name",
    "filename",
    "version_id",
    "download_source"
)


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
    main_minecraft_versions: Collection[str] = re.findall(
        f"{r"\A"}.*mc(?P<minecraft_version>{UnsanitisedMinecraftVersionValidator.UNSANITISED_MINECRAFT_VERSION_RE.strip(r"\AZ")}).*{r"\Z"}",
        filename
    )
    backup_minecraft_versions: Collection[str] = re.findall(
        f"{r"\A"}.*(?P<minecraft_version>{UnsanitisedMinecraftVersionValidator.UNSANITISED_MINECRAFT_VERSION_RE.strip(r"\AZ")}).*{r"\Z"}",
        filename
    )

    if not main_minecraft_versions:
        if not backup_minecraft_versions:
            return None

        return next(iter(backup_minecraft_versions))

    return next(iter(main_minecraft_versions))


def setup_raw_mods_list(*, mods_list_file: TextIOWrapper | None, mods_list: str | None, force_env_variables: bool = False) -> None:  # noqa: E501
    filename_minecraft_version: str | None = None
    filename_mod_loader: ModLoader | None = None
    if mods_list is not None or mods_list_file is not None:
        file_path: Path
        for file_path in Path().iterdir():
            temp_filename_minecraft_version: str | None = get_minecraft_version_from_filename(
                file_path.name
            )
            filename_minecraft_version_is_empty: bool = bool(
                temp_filename_minecraft_version is not None
                and filename_minecraft_version is None
            )
            if filename_minecraft_version_is_empty:
                filename_minecraft_version = temp_filename_minecraft_version

            temp_filename_mod_loader: ModLoader | None = config.get_mod_loader_from_filename(
                file_path.name
            )
            filename_mod_loader_is_empty: bool = bool(
                temp_filename_mod_loader is not None
                and filename_mod_loader is None
            )
            if filename_mod_loader_is_empty:
                filename_mod_loader = temp_filename_mod_loader

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

            filename_minecraft_version = get_minecraft_version_from_filename(
                mods_list_file_path.name
            )

        else:
            mods_list = mods_list_file.read()

    load_from_str(
        mods_list,
        known_minecraft_version=filename_minecraft_version,
        known_mod_loader=filename_mod_loader
    )


def load_from_iterable_of_mappings(raw_mods_list_collection: Iterable[Mapping[str, object]], *, known_minecraft_version: str | None = None, known_mod_loader: ModLoader | None = None) -> None:
    mod_details: Mapping[str, object] | str
    for mod_details in raw_mods_list_collection:
        if isinstance(mod_details, str):
            mod_details = mod_details.strip(", \t\n")
            if "," not in mod_details:
                load_from_single_depth_iterable(
                    [mod_details],
                    known_minecraft_version=known_minecraft_version,
                    known_mod_loader=known_mod_loader
                )
                continue

            load_from_multi_depth_iterable(
                [mod_details],
                known_minecraft_version=known_minecraft_version,
                known_mod_loader=known_mod_loader
            )
            continue

        all_keys_are_valid: bool = bool(
            all(key in mod_details for key in REQUIRED_DETAILED_MOD_KEYS)
            and all(
                isinstance(mod_details.get(key, ""), str)
                for key
                in set(REQUIRED_DETAILED_MOD_KEYS) | {"download_source"}
            )
        )
        if not all_keys_are_valid:
            raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)

        if "minecraft_version" in mod_details:
            if not isinstance(mod_details["minecraft_version"], str):
                raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)

            if mod_details["minecraft_version"]:
                known_minecraft_version = mod_details["minecraft_version"]

        if "mod_loader" in mod_details:
            if not isinstance(mod_details["mod_loader"], str):
                raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)

            if mod_details["mod_loader"]:
                known_mod_loader = mod_details["mod_loader"]

        instance_defaults: dict[str, object] = {
            "name": mod_details["name"],
            "version_id": mod_details["version_id"]
        }

        ModClass: type[DetailedMod]
        download_source_is_curseforge: bool = bool(
            mod_details["download_source"] == "CF"
            or (
                mod_details["download_source"].replace(" ", "").replace("-", "").replace(
                    "_",
                    ""
                ).lower().strip() == "curseforge"
            )
        )
        download_source_is_modrinth: bool = bool(
            mod_details["download_source"] == "MR"
            or (
                mod_details["download_source"].replace(" ", "").replace("-", "").replace(
                    "_",
                    ""
                ).lower().strip() == "modrinth"
            )
        )
        if download_source_is_curseforge:
            ModClass = APISourceMod
            api_mod_id_is_valid: bool = bool(
                "api_mod_id" in mod_details
                and isinstance(mod_details["api_mod_id"], str)
            )
            if not api_mod_id_is_valid:
                raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)
            instance_defaults.update(
                {
                    "api_source": APISourceMod.APISource.CURSEFORGE,
                    "api_mod_id": mod_details["api_mod_id"].strip()
                }
            )
        elif download_source_is_modrinth:
            ModClass = APISourceMod
            api_mod_id_is_valid: bool = bool(
                "api_mod_id" in mod_details
                and isinstance(mod_details["api_mod_id"], str)
            )
            if not api_mod_id_is_valid:
                raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)
            instance_defaults.update(
                {
                    "api_source": APISourceMod.APISource.MODRINTH,
                    "api_mod_id": mod_details["api_mod_id"].strip()
                }
            )
        else:
            ModClass = CustomSourceMod
            instance_defaults["download_url"] = mod_details["download_source"].strip()

        if "disabled" in mod_details:
            if not isinstance(mod_details["disabled"], bool):
                raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)
            instance_defaults["disabled"] = mod_details["disabled"]

        if "tags" in mod_details:
            if not isinstance(mod_details["tags"], Iterable):
                raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)

            tag_type_checking: object
            for tag_type_checking in mod_details["tags"]:
                if not isinstance(tag_type_checking, str):
                    raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)

        created_mod: DetailedMod
        mod_was_created: bool
        e: ValidationError
        try:
            created_mod, mod_was_created = ModClass.objects.get_or_create(
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
                _unique_identifier=mod_details["filename"].strip(),
                defaults=instance_defaults
            )
        except ValidationError as e:
            raise ModListEntryLoadError(
                unique_identifier=mod_details["filename"].strip(),
                reason=e
            ) from None

        if "tags" in mod_details:
            tag: str
            for tag in mod_details["tags"]:
                tag = tag.lower().strip(", \t\n").replace("_", "-").replace(
                    " ", "-"
                )

                if not tag:
                    continue

                created_mod_tag: ModTag
                mod_tag_was_created: bool
                try:
                    created_mod_tag, mod_tag_was_created = ModTag.objects.get_or_create(
                        name=tag
                    )
                except ValidationError as e:
                    raise ModTagLoadError(
                        name=tag,
                        mod_unique_identifier=mod_details["filename"].strip(),
                        reason=e
                    ) from None

                if mod_tag_was_created:
                    logging.debug(f"Successfully created mod-tag object: {created_mod_tag!r}")
                else:
                    logging.debug(f"Retrieved {created_mod_tag!r} (already existed)")

                created_mod.tags.add(created_mod_tag)
                logging.debug(
                    f"Successfully added mod-tag object: {created_mod_tag!r} "
                    f"to currently loaded mod object: {created_mod!r}"
                )

        if mod_was_created:
            logging.debug(f"Successfully created mod object: {created_mod!r}")
        else:
            logging.debug(f"Retrieved {created_mod!r} (already existed)")


def load_from_mapping(raw_mods_list_dict: Mapping[str, object], *, known_minecraft_version: str | None = None, known_mod_loader: ModLoader | None = None) -> None:
    if all(key in raw_mods_list_dict for key in REQUIRED_DETAILED_MOD_KEYS):
        load_from_iterable_of_mappings(raw_mods_list_collection=(raw_mods_list_dict,))
        return

    key: str
    value: object
    for key, value in raw_mods_list_dict.items():
        key_minecraft_version: str | None = get_minecraft_version_from_filename(key)
        if key_minecraft_version:
            known_minecraft_version = key_minecraft_version

        key_mod_loader: ModLoader | None = config.get_mod_loader_from_filename(key)
        if key_mod_loader:
            known_mod_loader = key_mod_loader

        if isinstance(value, Mapping):
            load_from_mapping(
                value,
                known_minecraft_version=known_minecraft_version,
                known_mod_loader=known_mod_loader
            )
            continue

        if isinstance(value, Sequence):
            is_array_of_strings: bool = all(
                isinstance(inner_object, str)
                for inner_object
                in random.sample(value, (len(value) // 2) if (len(value) // 2) > 0 else 1)
            )
            is_array_of_mappings: bool = all(
                isinstance(inner_object, Mapping)
                for inner_object
                in random.sample(value, (len(value) // 2) if (len(value) // 2) > 0 else 1)
            )
            if is_array_of_strings:
                load_from_single_depth_iterable(
                    value,
                    known_minecraft_version=known_minecraft_version,
                    known_mod_loader=known_mod_loader
                )
                continue

            if is_array_of_mappings:
                load_from_iterable_of_mappings(
                    value,
                    known_minecraft_version=known_minecraft_version,
                    known_mod_loader=known_mod_loader
                )
                continue

            raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)

        raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)


def load_from_single_depth_iterable(raw_mods_list_iterable: Iterable[str], *, known_minecraft_version: str | None = None, known_mod_loader: ModLoader | None = None) -> None:
    raw_identifier: str
    for raw_identifier in raw_mods_list_iterable:
        if not raw_identifier:
            continue

        e: ValidationError
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

    filename_minecraft_version: str | None = get_minecraft_version_from_filename(
        raw_mod_details_collection[1].strip()
    )
    if filename_minecraft_version:
        known_minecraft_version = filename_minecraft_version

    filename_mod_loader: str | None = config.get_mod_loader_from_filename(
        raw_mod_details_collection[1].strip()
    )
    if filename_mod_loader:
        known_mod_loader = filename_mod_loader

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
                if len(raw_mod_details_collection) > 5:
                    known_minecraft_version = raw_mod_details_collection[5].strip()

                if len(raw_mod_details_collection) > 6:
                    known_mod_loader = ModLoader(
                        raw_mod_details_collection[6].strip().upper()[:2]
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
                if len(raw_mod_details_collection) > 4:
                    known_minecraft_version = raw_mod_details_collection[4].strip()

                if len(raw_mod_details_collection) > 5:
                    known_mod_loader = ModLoader(
                        raw_mod_details_collection[5].strip().upper()[:2]
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
        raw_tags: set[str]
        if raw_mod_details.count("\"") == 0:
            raw_mod_details_collection = raw_mod_details.split(",")
            raw_tags = set(raw_mod_details_collection.pop(3).strip(", \t\n").split(","))

        elif raw_mod_details.count("\"") == 2:
            escaped_raw_mod_details: list[str] = raw_mod_details.split("\"", maxsplit=2)
            raw_tags = set(escaped_raw_mod_details[1].strip(", \t\n").split(","))

            speech_marks_usage_is_correct: bool = bool(
                escaped_raw_mod_details[0].endswith(",")
                and escaped_raw_mod_details[2].startswith(",")
            )
            if not speech_marks_usage_is_correct:
                raise ValueError("Incorrect usage of speech marks in mods-list")

            raw_mod_details_collection = (
                escaped_raw_mod_details[0].strip(", \t\n").split(",")
                + escaped_raw_mod_details[2].strip(", \t\n").split(",")
            )

        else:
            raise ValueError("Incorrect usage of speech marks in mods-list")

        if len(raw_mod_details_collection) > 8:
            raise ValueError("Too many values supplied for a single mod's details")

        created_mod: DetailedMod
        mod_was_created: bool

        api_source_is_curseforge: bool = bool(
            "curse" in raw_mod_details_collection[3].lower()
            or "FO" in raw_mod_details_collection[3].upper()
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

        tag: str
        for tag in raw_tags:
            tag = tag.lower().strip(", \t\n").replace("_", "-").replace(
                " ",
                "-"
            )

            if not tag:
                continue

            created_mod_tag: ModTag
            mod_tag_was_created: bool
            try:
                created_mod_tag, mod_tag_was_created = ModTag.objects.get_or_create(name=tag)
            except ValidationError as e:
                raise ModTagLoadError(
                    name=tag,
                    mod_unique_identifier=raw_mod_details_collection[1].strip(),
                    reason=e
                ) from None

            if mod_tag_was_created:
                logging.debug(f"Successfully created mod-tag object: {created_mod_tag!r}")
            else:
                logging.debug(f"Retrieved {created_mod_tag!r} (already existed)")

            created_mod.tags.add(created_mod_tag)
            logging.debug(
                f"Successfully added mod-tag object: {created_mod_tag!r} "
                f"to currently loaded mod object: {created_mod!r}"
            )

        if mod_was_created:
            logging.debug(f"Successfully created mod object: {created_mod!r}")
        else:
            logging.debug(f"Retrieved {created_mod!r} (already existed)")


def load_from_str(raw_mods_list: str, *, known_minecraft_version: str | None = None, known_mod_loader: ModLoader | None = None) -> None:
    raw_mods_list_collection: Sequence[str]

    try:
        raw_mods_list_mapping: JsonOutput = json.loads(raw_mods_list)
    except json.JSONDecodeError:
        raw_mods_list_collection = raw_mods_list.splitlines()
    else:
        if not raw_mods_list_mapping:
            raise ValueError(EMPTY_MODS_LIST_MESSAGE)

        if isinstance(raw_mods_list_mapping, float | int | bool | None):
            raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)

        if isinstance(raw_mods_list_mapping, Mapping):
            load_from_mapping(
                raw_mods_list_mapping,
                known_minecraft_version=known_minecraft_version,
                known_mod_loader=known_mod_loader
            )
            return

        if isinstance(raw_mods_list_mapping, str):
            load_from_single_depth_iterable(
                raw_mods_list.strip("\n").split(","),
                known_minecraft_version=known_minecraft_version,
                known_mod_loader=known_mod_loader
            )
            return

        if isinstance(raw_mods_list_mapping, Sequence):
            IS_ARRAY_OF_MAPPINGS: Final[bool] = all(
                isinstance(inner_object, Mapping)
                for inner_object
                in random.sample(
                    raw_mods_list_mapping,
                    (
                        len(raw_mods_list_mapping) // 2
                        if (len(raw_mods_list_mapping) // 2) > 0
                        else 1
                    )
                )
            )
            if IS_ARRAY_OF_MAPPINGS:
                IS_DATA_DUMP_MAPPING: Final[bool] = all(
                    bool(
                        set(inner_mapping.keys()).issubset({"model", "fields", "pk"})
                        and {"model", "fields"}.issubset(set(inner_mapping.keys()))
                    )
                    for inner_mapping
                    in random.sample(
                        raw_mods_list_mapping,
                        (
                            len(raw_mods_list_mapping) // 2
                            if (len(raw_mods_list_mapping) // 2) > 0
                            else 1
                        )
                    )
                )
                if IS_DATA_DUMP_MAPPING:
                    DESERIALIZED_OBJECTS: Final[Iterator[DeserializedObject]] = serializers.deserialize(
                        "json",
                        raw_mods_list
                    )
                    for deserialized_object in DESERIALIZED_OBJECTS:
                        deserialized_object.save()
                    return

                load_from_iterable_of_mappings(
                    raw_mods_list_mapping,  # type: ignore[arg-type]
                    known_minecraft_version=known_minecraft_version,
                    known_mod_loader=known_mod_loader
                )
                return

            IS_ARRAY_OF_ARRAYS: Final[bool] = all(
                isinstance(inner_object, Sequence)
                for inner_object
                in random.sample(
                    raw_mods_list_mapping,
                    (
                        len(raw_mods_list_mapping) // 2
                        if (len(raw_mods_list_mapping) // 2) > 0
                        else 1
                    )
                )
            )
            if IS_ARRAY_OF_ARRAYS:
                IS_INNER_ARRAY_OF_STRINGS: Final[bool] = all(
                    all(
                        isinstance(inner_inner_object, str)
                        for inner_inner_object
                        in inner_object
                    )
                    for inner_object
                    in random.sample(
                        raw_mods_list_mapping,
                        (
                            len(raw_mods_list_mapping) // 2
                            if (len(raw_mods_list_mapping) // 2) > 0
                            else 1
                        )
                    )
                )
                if IS_INNER_ARRAY_OF_STRINGS:
                    try:
                        raw_mods_list_collection = (
                            [",".join(inner_object) for inner_object in raw_mods_list_mapping]
                        )
                    except TypeError:
                        raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE) from None

                else:
                    raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)

            else:
                raw_mods_list_collection = (
                    [str(inner_object) for inner_object in raw_mods_list_mapping]
                )

        else:
            raise ValueError(INVALID_MODS_LIST_MAPPING_MESSAGE)

    if len(raw_mods_list_collection) == 0:
        raise ValueError(EMPTY_MODS_LIST_MESSAGE)

    if len(raw_mods_list_collection) == 1:
        load_from_single_depth_iterable(
            raw_mods_list.strip("\n").split(","),
            known_minecraft_version=known_minecraft_version,
            known_mod_loader=known_mod_loader
        )
        return

    IS_SINGLE_DEPTH: Final[bool] = all(
        "," not in raw_identifier.strip(", \t\n")
        for raw_identifier
        in random.sample(
            raw_mods_list_collection,
            (
                len(raw_mods_list_collection) // 2
                if (len(raw_mods_list_collection) // 2) > 0
                else 1
            )
        )
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
