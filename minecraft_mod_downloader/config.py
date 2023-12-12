"""
Contains settings values and import & setup functions.

Settings values are imported from the .env file or the current environment variables.
These values are used to configure the functionality of the bot at run-time.
"""

from collections.abc import Sequence

__all__: Sequence[str] = (
    "TRUE_VALUES",
    "FALSE_VALUES",
    "settings",
    "setup_env_variables",
    "setup_django",
    "IS_ENV_VARIABLES_SETUP",
    "IS_DJANGO_SETUP"
)

import logging
import os
import re
import platform
from pathlib import Path
from typing import Any, ClassVar, Final, Self, final
from identify import identify

import django
import dotenv

from minecraft_mod_downloader.exceptions import ConfigSettingRequiredError, ImproperlyConfiguredError

TRUE_VALUES: Final[frozenset[str]] = frozenset({"true", "1", "t", "y", "yes", "on"})
FALSE_VALUES: Final[frozenset[str]] = frozenset({"false", "0", "f", "n", "no", "off"})


# def get_mods_list(raw_mods_list: str) -> Iterable[str | ]


def get_default_minecraft_installation_directory_path() -> Path:
    system: str = platform.system()
    if system == "Windows":
        windows_minecraft_installation_directory_path: Path = (
            Path(os.getenv('APPDATA')) / ".minecraft"
        )
        if windows_minecraft_installation_directory_path.is_dir():
            return windows_minecraft_installation_directory_path

    if system == "Linux":
        linux_minecraft_installation_directory_path: Path = Path.home() / ".minecraft"
        if linux_minecraft_installation_directory_path.is_dir():
            return linux_minecraft_installation_directory_path

        linux_minecraft_installation_directory_path = (
            Path.home() / ".var/app/com.mojang.Minecraft/.minecraft"
        )
        if linux_minecraft_installation_directory_path.is_dir():
            return linux_minecraft_installation_directory_path

    if system == "Darwin":
        macos_minecraft_installation_directory_path: Path = (
            Path.home() / "Library/Application Support/minecraft"
        )
        if macos_minecraft_installation_directory_path.is_dir():
            return macos_minecraft_installation_directory_path

    INDETERMINABLE_MINECRAFT_INSTALLATION_DIRECTORY_PATH_MESSAGE: Final[str] = (
        "MINECRAFT_INSTALLATION_DIRECTORY_PATH could not be determined, "
        "because either Minecraft is not installable on your Operating System, "
        f"or no `.minecraft` directory exists."
    )
    raise OSError(INDETERMINABLE_MINECRAFT_INSTALLATION_DIRECTORY_PATH_MESSAGE)


@final
class Settings:
    """
    Settings class that provides access to all settings values.

    Settings values can be accessed via key (like a dictionary) or via class attribute.
    """

    _instance: ClassVar[Self | None] = None

    @classmethod
    def get_invalid_settings_key_message(cls, item: str) -> str:
        return f"{item!r} is not a valid settings key."

    # noinspection PyTypeHints
    def __new__(cls, *args: object, **kwargs: object) -> Self:
        """
        Return the singleton settings container instance.

        If no singleton instance exists, a new one is created, then stored as a class variable.
        """
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self) -> None:
        """Instantiate a new settings container with False is_setup flags."""
        self._is_env_variables_setup: bool = False
        self._is_django_setup: bool = False
        self._settings: dict[str, object] = {}

    def __getattr__(self, item: str) -> Any:
        """Retrieve settings value by attribute lookup."""
        self._setup_env_variables(
            mods_list_file_path=None,
            mods_list=None,
            minecraft_installation_directory_path=None,
            curseforge_api_key=None
        )

        if item in self._settings:
            return self._settings[item]

        if re.match(r"\A[A-Z](?:[A-Z_]*[A-Z])?\Z", item):
            INVALID_SETTINGS_KEY_MESSAGE: Final[str] = self.get_invalid_settings_key_message(
                item
            )
            raise AttributeError(INVALID_SETTINGS_KEY_MESSAGE)

        MISSING_ATTRIBUTE_MESSAGE: Final[str] = (
            f"{type(self).__name__!r} object has no attribute {item!r}"
        )
        raise AttributeError(MISSING_ATTRIBUTE_MESSAGE)

    def __getitem__(self, item: str) -> Any:
        """Retrieve settings value by key lookup."""
        e: AttributeError
        try:
            return getattr(self, item)
        except AttributeError as e:
            key_error_message: str = item

            if self.get_invalid_settings_key_message(item) in str(e):
                key_error_message = str(e)

            raise KeyError(key_error_message) from None

    def _setup_mods_list(self, mods_list_file_path: Path | None, mods_list: str | None) -> None:  # TODO: get list out of file
        raw_mods_list_file_path: str = os.getenv("MODS_LIST_FILE_PATH", "")
        if raw_mods_list_file_path:
            mods_list_file_path = Path(raw_mods_list_file_path)

        if mods_list is None:
            if not raw_mods_list_file_path and mods_list_file_path is None:
                MODS_LIST_FILE_PATH_NOT_PROVIDED_MESSAGE: Final[str] = (
                    "MODS_LIST_FILE_PATH has not been provided. "
                    "Please provide a valid path to your mods-list file, "
                    "either via the `--mods-list-file-path` CLI argument, "
                    "or the MODS_LIST_FILE_PATH environment variable."
                )
                raise ConfigSettingRequiredError(MODS_LIST_FILE_PATH_NOT_PROVIDED_MESSAGE)
            if raw_mods_list_file_path:
                mods_list_file_path = Path(raw_mods_list_file_path)
            if not mods_list_file_path.is_file():
                INVALID_MODS_LIST_FILE_PATH_MESSAGE: Final[str] = (
                    "MODS_LIST_FILE_PATH must be a valid path to your mods-list file."
                )
                raise ImproperlyConfiguredError(INVALID_MODS_LIST_FILE_PATH_MESSAGE)
        self._settings["MODS_LIST_FILE_PATH"] = mods_list_file_path

    def _setup_minecraft_installation_directory_path(self, minecraft_installation_directory_path: Path | None) -> None:
        raw_minecraft_installation_directory_path: str = os.getenv(
            "MINECRAFT_INSTALLATION_DIRECTORY_PATH",
            ""
        )

        if minecraft_installation_directory_path is None:
            minecraft_installation_directory_path = (
                Path(
                    raw_minecraft_installation_directory_path
                )
                if raw_minecraft_installation_directory_path
                else self.get_default_minecraft_installation_directory_path()
            )

        path_is_valid_minecraft_installation_directory: bool = bool(
            minecraft_installation_directory_path.is_dir()
            and (minecraft_installation_directory_path / "assets").is_dir()
            and (minecraft_installation_directory_path / "clientID.txt").is_file()
            and (
                tag in identify.tags_from_path(
                    minecraft_installation_directory_path / "clientID.txt"
                )
                for tag
                in ("file", "text", "plain-text")
            )
            and (minecraft_installation_directory_path / "launcher_accounts.json").is_file()
            and (
                tag in identify.tags_from_path(
                    minecraft_installation_directory_path / "launcher_accounts.json"
                )
                for tag
                in ("file", "text", "json")
            )
            and (minecraft_installation_directory_path / "options.txt").is_file()
            and (
                tag in identify.tags_from_path(
                    minecraft_installation_directory_path / "launcher_accounts.json"
                )
                for tag
                in ("file", "text", "plain-text")
            )
        )

        if not path_is_valid_minecraft_installation_directory:
            INVALID_MINECRAFT_INSTALLATION_DIRECTORY_PATH_MESSAGE: Final[str] = (
                "MINECRAFT_INSTALLATION_DIRECTORY_PATH must be a valid path "
                "to your Minecraft installation directory."
            )
            raise ImproperlyConfiguredError(
                INVALID_MINECRAFT_INSTALLATION_DIRECTORY_PATH_MESSAGE
            )

        self._settings["MINECRAFT_INSTALLATION_DIRECTORY_PATH"] = (
            minecraft_installation_directory_path
        )

    def _setup_curseforge_api_key(self, curseforge_api_key: str | None) -> None:
        raw_curseforge_api_key: str = os.getenv(
            "CURSEFORGE_API_KEY",
            ""
        )

        if curseforge_api_key is None:
            if not raw_curseforge_api_key:
                logging.warning(
                    "CURSEFORGE_API_KEY has not been provided. "
                    "If any mods need to be downloaded from CurseForge, "
                    "they will fail to be downloaded. "
                    "Provide your CurseForge API Key, "
                    "either via the `--curseforge-api-key` CLI argument, "
                    "or the CURSEFORGE_API_KEY environment variable."
                )
                return

            curseforge_api_key = raw_curseforge_api_key

        if not re.match(r"\A[A-Za-z0-9$/.]{60}\Z", curseforge_api_key):
            INVALID_CURSEFORGE_API_KEY_MESSAGE: Final[str] = (
                "CURSEFORGE_API_KEY must be a valid CurseForge API Key "
                "(see https://console.curseforge.com/?#/api-keys "
                "for how to generate CurseForge API keys)."
            )
            raise ImproperlyConfiguredError(INVALID_CURSEFORGE_API_KEY_MESSAGE)

        self._settings["CURSEFORGE_API_KEY"] = curseforge_api_key

    def _setup_env_variables(self, mods_list_file_path: Path | None, mods_list: str | None, minecraft_installation_directory_path: Path | None, curseforge_api_key: str | None) -> None:
        """
        Load environment values into the settings dictionary.

        Environment values are loaded from the .env file/the current environment variables and
        are only stored after the input values have been validated.
        """
        if not self._is_env_variables_setup:
            dotenv.load_dotenv()

            self._setup_mods_list(mods_list_file_path=mods_list_file_path, mods_list=mods_list)

            self._setup_minecraft_installation_directory_path(
                minecraft_installation_directory_path=minecraft_installation_directory_path
            )

            self._setup_curseforge_api_key(curseforge_api_key=curseforge_api_key)

            self._is_env_variables_setup = True

    def _setup_django(self) -> None:
        """
        Load the correct settings module into the Django process.

        Scripts cannot access model instances & database data until
        Django's settings module has been loaded.
        """
        if not self._is_django_setup:
            os.environ["DJANGO_SETTINGS_MODULE"] = "minecraft_mod_downloader.models._settings"
            django.setup()

            self._is_django_setup = True


settings: Final[Settings] = Settings()


def setup_env_variables(mods_list_file_path: Path, mods_list: str, minecraft_installation_directory_path: Path, curseforge_api_key: str) -> None:  # noqa: E501
    """
    Load environment values into the settings dictionary.

    Environment values are loaded from the .env file/the current environment variables and
    are only stored after the input values have been validated.
    """
    # noinspection PyProtectedMember
    settings._setup_env_variables(  # noqa: SLF001
        mods_list_file_path=mods_list_file_path,
        mods_list=mods_list,
        minecraft_installation_directory_path=minecraft_installation_directory_path,
        curseforge_api_key=curseforge_api_key
    )


def setup_django() -> None:
    """
    Load the correct settings module into the Django process.

    Scripts cannot access model instances & database data until
    Django's settings module has been loaded.
    """
    # noinspection PyProtectedMember
    settings._setup_django()  # noqa: SLF001


IS_ENV_VARIABLES_SETUP: bool
IS_DJANGO_SETUP: bool


def __getattr__(item: str) -> object:
    if item == "IS_ENV_VARIABLES_SETUP":
        # noinspection PyProtectedMember
        return settings._is_env_variables_setup  # noqa: SLF001

    if item == "IS_DJANGO_SETUP":
        # noinspection PyProtectedMember
        return settings._is_django_setup  # noqa: SLF001

    MODULE_ATTRIBUTE_ERROR_MESSAGE: Final[str] = (
        f"module {__name__!r} has no attribute {item!r}"
    )
    raise AttributeError(MODULE_ATTRIBUTE_ERROR_MESSAGE)
