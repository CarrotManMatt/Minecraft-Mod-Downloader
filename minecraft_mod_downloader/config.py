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
from collections.abc import Iterable
from pathlib import Path
from typing import Any, ClassVar, Final, Self, final
from identify import identify
from io import TextIOWrapper
from logging import Logger

import django
import dotenv

from minecraft_mod_downloader.exceptions import ConfigSettingRequiredError, ImproperlyConfiguredError
from minecraft_mod_downloader.parse_mods_list import add_mods_list_to_db

TRUE_VALUES: Final[frozenset[str]] = frozenset({"true", "1", "t", "y", "yes", "on"})
FALSE_VALUES: Final[frozenset[str]] = frozenset({"false", "0", "f", "n", "no", "off"})
LOG_LEVEL_CHOICES: Final[Sequence[str]] = (
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "NONE"
)


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

    MODS_LIST_FILE_NOT_PROVIDED_MESSAGE: Final[str] = (
        "MODS_LIST_FILE has not been provided. "
        "Please provide a valid mods-list file, "
        "either via the `--mods-list-file` CLI argument, "
        "or the MODS_LIST_FILE_PATH environment variable."
    )
    raise ConfigSettingRequiredError(MODS_LIST_FILE_NOT_PROVIDED_MESSAGE)


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
            mods_list_file=None,
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

    @staticmethod
    def _setup_logging(verbosity: int | None, force_env_variables: bool = False) -> None:
        log_level: str = (
            os.getenv("LOG_LEVEL", "" if force_env_variables else "INFO").upper()
            if verbosity is None or force_env_variables
            else (
                "NONE"
                if verbosity < 0
                else (
                    "ERROR"
                    if verbosity == 0
                    else (
                        "WARNING"
                        if verbosity == 1
                        else (
                            "INFO"
                            if verbosity == 2
                            else "DEBUG"
                        )
                    )
                )
            )
        )

        if log_level not in LOG_LEVEL_CHOICES:
            INVALID_LOG_LEVEL_MESSAGE: Final[str] = (
                f"LOG_LEVEL must be one of {",".join(
                    f"{log_level_choice!r}" for log_level_choice in LOG_LEVEL_CHOICES[:-1]
                )} or {LOG_LEVEL_CHOICES[-1]!r}."
            )
            raise ImproperlyConfiguredError(INVALID_LOG_LEVEL_MESSAGE)

        if log_level == "NONE":
            logger: Logger = logging.getLogger()
            logger.propagate = False
        else:
            # noinspection SpellCheckingInspection
            logging.basicConfig(
                level=getattr(logging, log_level),
                format="%(levelname)s: %(message)s"
            )

    @staticmethod
    def _setup_mods_list(*, mods_list_file: TextIOWrapper | None, mods_list: str | None, force_env_variables: bool = False) -> None:  # noqa: E501
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
                        "MODS_LIST_FILE_PATH must be a valid path to your mods-list file."
                        "Provide the path to your mods-list file, "
                        "either via the `--mods-list-file` CLI argument, "
                        "or the MODS_LIST_FILE_PATH environment variable."
                    )
                    raise ImproperlyConfiguredError(INVALID_MODS_LIST_FILE_PATH_MESSAGE)

                with mods_list_file_path.open("r") as mods_list_file:
                    mods_list = mods_list_file.read()

            else:
                mods_list = mods_list_file.read()

        add_mods_list_to_db(mods_list)

    def _setup_minecraft_installation_directory_path(self, *, minecraft_installation_directory_path: Path | None, force_env_variables: bool = False) -> None:  # noqa: E501
        if minecraft_installation_directory_path is None or force_env_variables:
            raw_minecraft_installation_directory_path: str = os.getenv(
                "MINECRAFT_INSTALLATION_DIRECTORY_PATH",
                ""
            )

            minecraft_installation_directory_path = (
                Path(
                    raw_minecraft_installation_directory_path
                )
                if raw_minecraft_installation_directory_path or force_env_variables
                else get_default_minecraft_installation_directory_path()
            )

        def _identify_tags_from_path(path: Path) -> set[str]:
            return identify.tags_from_path(path)  # type: ignore[arg-type]

        path_is_valid_minecraft_installation_directory: bool = bool(
            minecraft_installation_directory_path.is_dir()
            and (minecraft_installation_directory_path / "assets").is_dir()
            and (minecraft_installation_directory_path / "clientID.txt").is_file()
            and (
                tag in _identify_tags_from_path(
                    minecraft_installation_directory_path / "clientID.txt"
                )
                for tag
                in ("file", "text", "plain-text")
            )
            and (minecraft_installation_directory_path / "launcher_accounts.json").is_file()
            and (
                tag in _identify_tags_from_path(
                    minecraft_installation_directory_path / "launcher_accounts.json"
                )
                for tag
                in ("file", "text", "json")
            )
            and (minecraft_installation_directory_path / "options.txt").is_file()
            and (
                tag in _identify_tags_from_path(
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
                "Provide the path to your Minecraft installation directory, "
                "either via the `--minecraft-installation-directory-path` CLI argument, "
                "or the MINECRAFT_INSTALLATION_DIRECTORY_PATH environment variable."
            )
            raise ImproperlyConfiguredError(
                INVALID_MINECRAFT_INSTALLATION_DIRECTORY_PATH_MESSAGE
            )

        self._settings["MINECRAFT_INSTALLATION_DIRECTORY_PATH"] = (
            minecraft_installation_directory_path
        )

    def _setup_curseforge_api_key(self, *, curseforge_api_key: str | None, force_env_variables: bool = False) -> None:  # noqa: E501
        if curseforge_api_key is None or force_env_variables:
            raw_curseforge_api_key: str = os.getenv(
                "CURSEFORGE_API_KEY",
                ""
            )

            if not raw_curseforge_api_key:
                logging.warning(
                    "CURSEFORGE_API_KEY has not been provided. "
                    "If any mods need to be downloaded from CurseForge, "
                    "they will fail to be downloaded. "
                    "Provide your CurseForge API Key, "
                    "either via the `--curseforge-api-key` CLI argument, "
                    "or the CURSEFORGE_API_KEY environment variable."
                )

                self._settings["CURSEFORGE_API_KEY"] = None
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

    def _setup_env_variables(self, *, mods_list_file: TextIOWrapper | None, mods_list: str | None, minecraft_installation_directory_path: Path | None, curseforge_api_key: str | None, force_env_variables: bool = False, verbosity: int = 1) -> None:
        """
        Load environment values into the settings dictionary.

        Environment values are loaded from the .env file/the current environment variables and
        are only stored after the input values have been validated.
        """
        if not self._is_env_variables_setup:
            dotenv.load_dotenv()

            self._setup_logging(verbosity=verbosity, force_env_variables=force_env_variables)

            self._setup_mods_list(
                mods_list_file=mods_list_file,
                mods_list=mods_list,
                force_env_variables=force_env_variables
            )

            self._setup_minecraft_installation_directory_path(
                minecraft_installation_directory_path=minecraft_installation_directory_path,
                force_env_variables=force_env_variables
            )

            self._setup_curseforge_api_key(
                curseforge_api_key=curseforge_api_key,
                force_env_variables=force_env_variables
            )

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


def setup_env_variables(*, mods_list_file: TextIOWrapper, mods_list: str, minecraft_installation_directory_path: Path, curseforge_api_key: str, force_env_variables: bool, verbosity: int) -> None:  # noqa: E501
    """
    Load environment values into the settings dictionary.

    Environment values are loaded from the .env file/the current environment variables and
    are only stored after the input values have been validated.
    """
    # noinspection PyProtectedMember
    settings._setup_env_variables(  # noqa: SLF001
        mods_list_file=mods_list_file,
        mods_list=mods_list,
        minecraft_installation_directory_path=minecraft_installation_directory_path,
        curseforge_api_key=curseforge_api_key,
        force_env_variables=force_env_variables,
        verbosity=verbosity
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
