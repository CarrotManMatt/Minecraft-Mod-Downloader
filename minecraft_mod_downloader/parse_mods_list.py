from collections.abc import Sequence

__all__: Sequence[str] = (
    "get_default_mods_list_file_path",
    "setup_raw_mods_list",
    "load_from_mapping",
    "load_from_single_depth_iterable",
    "load_from_multi_depth_iterable",
    "load_from_str"
)

import os
from collections.abc import Iterable, Mapping, Collection
import json
from io import TextIOWrapper
from pathlib import Path
from typing import Final, Any

from django.core.exceptions import ValidationError

from minecraft_mod_downloader.config import settings
from minecraft_mod_downloader.exceptions import ConfigSettingRequiredError, ImproperlyConfiguredError, ModListEntryLoadError
from minecraft_mod_downloader.models import SimpleMod


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


def setup_raw_mods_list(*, mods_list_file: TextIOWrapper | None, mods_list: str | None, force_env_variables: bool = False) -> None:  # noqa: E501
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

        else:
            mods_list = mods_list_file.read()

    load_from_str(mods_list)


def load_from_mapping(raw_mods_list_dict: Mapping[str, Any]) -> None:
    raise NotImplementedError()  # TODO


def load_from_single_depth_iterable(raw_mods_list_iterable: Iterable[str]) -> None:
    raw_identifier: str
    for raw_identifier in raw_mods_list_iterable:
        try:
            SimpleMod.objects.get_or_create(
                _unique_identifier=raw_identifier,
                minecraft_version=settings["FILTER_MINECRAFT_VERSION"],
                mod_loader=settings["FILTER_MOD_LOADER"]
            )
        except ValidationError as e:
            raise ModListEntryLoadError(
                unique_identifier=raw_identifier, reason=e
            ) from None



def load_from_multi_depth_iterable(raw_mods_list_iterable: Iterable[Iterable[str]]) -> None:
    print(list(raw_mods_list_iterable))
    raise NotImplementedError()  # TODO


def load_from_str(raw_mods_list: str) -> None:
    try:
        raw_mods_list_mapping: Mapping[str, Any] = json.loads(raw_mods_list)
    except json.JSONDecodeError:
        pass
    else:
        load_from_mapping(raw_mods_list_mapping)

    raw_mods_list_collection: Collection[str] = raw_mods_list.splitlines()

    if len(raw_mods_list_collection) == 0:
        EMPTY_MODS_LIST_ERROR: Final[str] = "Empty mods list."
        raise ValueError(EMPTY_MODS_LIST_ERROR)

    if len(raw_mods_list_collection) == 1:
        load_from_single_depth_iterable(raw_mods_list.strip("\n").split(","))

    else:
        load_from_multi_depth_iterable(
            raw_mod_details.split(",") for raw_mod_details in raw_mods_list_collection
        )
