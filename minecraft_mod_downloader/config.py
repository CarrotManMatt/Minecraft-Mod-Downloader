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
    "run_setup",
    "IS_ENV_VARIABLES_SETUP",
    "identify_tags_from_path",
    "minecraft_version_name_is_regex_valid",
    "minecraft_version_path_is_valid",
    "minecraft_versions_directory_path_contains_a_valid_version",
    "get_default_minecraft_installation_directory_path",
    "get_default_minecraft_mods_installation_directory_path",
    "get_default_minecraft_versions_directory_path",
    "get_mod_loader_from_filename",
    "get_default_mod_loader",
    "get_latest_installed_minecraft_version"
)

from django.core.exceptions import ValidationError

import logging
import os
import platform
import re
from logging import Logger
from pathlib import Path
from typing import Any, ClassVar, Final, Self, final

import dotenv
from identify import identify

from django.core import management
from django.core.validators import MinLengthValidator

from minecraft_mod_downloader.utils import SuppressStdOutAndStdErr, SuppressTraceback

from minecraft_mod_downloader.exceptions import ImproperlyConfiguredError
from minecraft_mod_downloader.models import BaseMod, MinecraftVersionValidator, ModLoader
from minecraft_mod_downloader.models import UnsanitisedMinecraftVersionValidator

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


def identify_tags_from_path(path: Path) -> set[str]:
    return identify.tags_from_path(path)  # type: ignore[arg-type]


def minecraft_version_name_is_regex_valid(minecraft_version_name: str) -> bool:
    try:
        MinecraftVersionValidator()(minecraft_version_name)
    except ValidationError:
        return False
    else:
        return True


def minecraft_version_path_is_valid(minecraft_version_path: Path) -> bool:
    return bool(
        minecraft_version_path.is_dir()
        and (
            (
                (
                    "FA" in minecraft_version_path.name.upper()
                    or "QU" in minecraft_version_path.name.upper()
                )
                and minecraft_version_name_is_regex_valid(
                    minecraft_version_path.name.split("-")[-1]
                    if minecraft_version_path.name.split("-")[-1].count(".") == 2
                    else minecraft_version_path.name.split("-")[-1] + ".0"
                )
                and 5 <= len(
                    minecraft_version_path.name.split("-")[-1]
                    if minecraft_version_path.name.split("-")[-1].count(".") == 2
                    else minecraft_version_path.name.split("-")[-1] + ".0"
                ) <= 9
            )
            or (
                "FO" in minecraft_version_path.name.upper()
                and minecraft_version_name_is_regex_valid(
                    minecraft_version_path.name.split("-")[0]
                    if minecraft_version_path.name.split("-")[0].count(".") == 2
                    else minecraft_version_path.name.split("-")[0] + ".0"
                )
                and 5 <= len(
                    minecraft_version_path.name.split("-")[0]
                    if minecraft_version_path.name.split("-")[0].count(".") == 2
                    else minecraft_version_path.name.split("-")[0] + ".0"
                ) <= 9
            )
        )
        and (minecraft_version_path / f"{minecraft_version_path.name}.json").is_file()
        and all(
            tag in identify_tags_from_path(
                minecraft_version_path / f"{minecraft_version_path.name}.json"
            )
            for tag
            in ("file", "text", "json")
        )
    )


def minecraft_versions_directory_path_contains_a_valid_version(_minecraft_versions_directory_path: Path) -> bool:  # noqa: E501
    minecraft_version_path: Path
    for minecraft_version_path in _minecraft_versions_directory_path.iterdir():
        if minecraft_version_path_is_valid(minecraft_version_path):
            return True

    return False


def get_default_minecraft_installation_directory_path() -> Path:
    default_minecraft_installation_directory_path: Path = Path.home() / ".minecraft"

    system: str = platform.system()
    if system == "Windows":  # noqa: PLR2004
        default_minecraft_installation_directory_path = (
            Path(os.environ["APPDATA"]) / ".minecraft"
        )

    elif system == "Linux":  # noqa: PLR2004
        if not default_minecraft_installation_directory_path.is_dir():
            default_minecraft_installation_directory_path = (
                Path.home() / ".var/app/com.mojang.Minecraft/.minecraft"
            )

    elif system == "Darwin":  # noqa: PLR2004
        default_minecraft_installation_directory_path = (
            Path.home() / "Library/Application Support/minecraft"
        )

    DEFAULT_MINECRAFT_INSTALLATION_DIRECTORY_PATH_IS_VALID: Final[bool] = bool(
        default_minecraft_installation_directory_path.is_dir()
        and (default_minecraft_installation_directory_path / "assets").is_dir()
        and (default_minecraft_installation_directory_path / "clientID.txt").is_file()
        and all(
            tag in identify_tags_from_path(
                default_minecraft_installation_directory_path / "clientID.txt"
            )
            for tag
            in ("file", "text", "plain-text")
        )
        and (
            default_minecraft_installation_directory_path / "launcher_accounts.json"
        ).is_file()
        and all(
            tag in identify_tags_from_path(
                default_minecraft_installation_directory_path / "launcher_accounts.json"
            )
            for tag
            in ("file", "text", "json")
        )
        and (default_minecraft_installation_directory_path / "options.txt").is_file()
        and all(
            tag in identify_tags_from_path(
                default_minecraft_installation_directory_path / "options.txt"
            )
            for tag
            in ("file", "text", "plain-text")
        )
    )
    if not DEFAULT_MINECRAFT_INSTALLATION_DIRECTORY_PATH_IS_VALID:
        INDETERMINABLE_MINECRAFT_INSTALLATION_DIRECTORY_PATH_MESSAGE: Final[str] = (
            "MINECRAFT_INSTALLATION_DIRECTORY_PATH could not be determined, "
            "because either Minecraft is not installable on your Operating System, "
            "or no `.minecraft` directory exists."
        )
        raise OSError(INDETERMINABLE_MINECRAFT_INSTALLATION_DIRECTORY_PATH_MESSAGE)

    return default_minecraft_installation_directory_path


def get_default_minecraft_mods_installation_directory_path() -> Path:
    default_minecraft_installation_directory_path: Path = (
        get_default_minecraft_installation_directory_path()
    )

    default_minecraft_mods_installation_directory_path: Path = (
        default_minecraft_installation_directory_path / "mods"
    )

    if not default_minecraft_mods_installation_directory_path.is_dir():
        default_minecraft_mods_installation_directory_path.mkdir()

    return default_minecraft_mods_installation_directory_path


def get_default_minecraft_versions_directory_path() -> Path:
    default_minecraft_installation_directory_path: Path = (
        get_default_minecraft_installation_directory_path()
    )

    default_minecraft_versions_directory_path: Path = (
        default_minecraft_installation_directory_path / "versions"
    )

    DEFAULT_MINECRAFT_VERSIONS_DIRECTORY_PATH_IS_VALID: Final[bool] = bool(
        default_minecraft_versions_directory_path.is_dir()
        and minecraft_versions_directory_path_contains_a_valid_version(
            default_minecraft_versions_directory_path
        )
    )
    if not DEFAULT_MINECRAFT_VERSIONS_DIRECTORY_PATH_IS_VALID:
        INDETERMINABLE_MINECRAFT_VERSIONS_DIRECTORY_PATH_MESSAGE: Final[str] = (
            "MINECRAFT_VERSIONS_DIRECTORY_PATH could not be determined, "
            "because no valid `.minecraft/versions` directory exists."
        )
        raise OSError(INDETERMINABLE_MINECRAFT_VERSIONS_DIRECTORY_PATH_MESSAGE)

    return default_minecraft_versions_directory_path


def get_mod_loader_from_filename(filename: str) -> ModLoader | None:
    if "FA" in filename.upper():
        return ModLoader.FABRIC

    if "QU" in filename.upper():
        return ModLoader.QUILT

    if "FO" in filename.upper():
        return ModLoader.FORGE

    return None


def get_default_mod_loader(minecraft_version: str, minecraft_versions_directory_path: Path) -> ModLoader:
    minecraft_version_path: Path
    for minecraft_version_path in minecraft_versions_directory_path.iterdir():
        compatible_mod_loader_found: bool = bool(
            minecraft_version.removesuffix(".0") in minecraft_version_path.name
            and minecraft_version_path_is_valid(minecraft_version_path)
        )
        if compatible_mod_loader_found:
            mod_loader: ModLoader | None = get_mod_loader_from_filename(
                minecraft_version_path.name
            )
            if mod_loader:
                return mod_loader

    return ModLoader("FA")


def get_latest_installed_minecraft_version(minecraft_versions_directory_path: Path) -> str:
    latest_installed_minecraft_version: str | None = None

    def next_version_is_latest(previous_version: str | None, next_version: str) -> bool:
        if previous_version is None:
            return True

        split_previous_version: tuple[str, str, str] = tuple(  # type: ignore[assignment]
            previous_version.split(".", maxsplit=2)
        )
        split_next_version: tuple[str, str, str] = tuple(  # type: ignore[assignment]
            next_version.split(".", maxsplit=2)
        )
        previous_major: int = int(split_previous_version[0])
        previous_minor: int = int(split_previous_version[1])
        previous_bugfix: int = int(split_previous_version[2])
        next_major: int = int(split_next_version[0])
        next_minor: int = int(split_next_version[1])
        next_bugfix: int = int(split_next_version[2])

        if next_major != previous_major:
            return next_major > previous_major

        if next_minor != previous_minor:
            return next_minor > previous_minor

        return next_bugfix > previous_bugfix

    minecraft_version_path: Path
    for minecraft_version_path in minecraft_versions_directory_path.iterdir():
        minecraft_version_path_is_modded: bool = bool(
            "FA" in minecraft_version_path.name.upper()
            or "QU" in minecraft_version_path.name.upper()
            or "FO" in minecraft_version_path.name.upper()
        )
        if not minecraft_version_path_is_modded:
            continue

        current_minecraft_version: str = (
            minecraft_version_path.name.split("-")[0]
            if "FO" in minecraft_version_path.name.upper()
            else minecraft_version_path.name.split("-")[-1]
        )
        minecraft_version_path_is_latest: bool = (
            minecraft_version_path_is_valid(minecraft_version_path)
            and next_version_is_latest(
                latest_installed_minecraft_version,
                (
                    current_minecraft_version
                    if current_minecraft_version.count(".") == 2
                    else current_minecraft_version + ".0"
                )
            )
        )
        if minecraft_version_path_is_latest:
            latest_installed_minecraft_version = current_minecraft_version

    if latest_installed_minecraft_version is None:
        INDETERMINABLE_LATEST_INSTALLED_MINECRAFT_VERSION_MESSAGE: Final[str] = (
            "FILTER_MINECRAFT_VERSION could not be automatically determined, "
            "because no versions are installed within your `.minecraft/versions` directory."
        )
        raise OSError(INDETERMINABLE_LATEST_INSTALLED_MINECRAFT_VERSION_MESSAGE)

    return latest_installed_minecraft_version


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
        self._settings: dict[str, object] = {}

    def __getattr__(self, item: str) -> Any:
        """Retrieve settings value by attribute lookup."""
        if not self._is_env_variables_setup:
            self._setup_env_variables(
                minecraft_mods_installation_directory_path=None,
                minecraft_versions_directory_path=None,
                curseforge_api_key=None,
                filter_minecraft_version=None,
                filter_mod_loader=None
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
    def _setup_logging(*, verbosity: int | None, force_env_variables: bool = False) -> None:
        log_level: str = (
            os.getenv("LOG_LEVEL", "" if force_env_variables else "INFO").upper()  # noqa: PLW1508
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
                            if verbosity == 2  # noqa: PLR2004
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

        if log_level == "NONE":  # noqa: PLR2004
            logger: Logger = logging.getLogger()
            logger.propagate = False
        else:
            # noinspection SpellCheckingInspection
            logging.basicConfig(
                level=getattr(logging, log_level),
                format="%(levelname)s: %(message)s"
            )

    def _setup_minecraft_mods_installation_directory_path(self, *, minecraft_mods_installation_directory_path: Path | None, force_env_variables: bool = False) -> None:  # noqa: E501
        extra_invalid_minecraft_mods_installation_directory_path_message: str = ""

        if minecraft_mods_installation_directory_path is None or force_env_variables:
            raw_minecraft_mods_installation_directory_path: str = os.getenv(
                "MINECRAFT_MODS_INSTALLATION_DIRECTORY_PATH",
                ""
            )

            minecraft_mods_installation_directory_path = (
                Path(raw_minecraft_mods_installation_directory_path)
                if raw_minecraft_mods_installation_directory_path or force_env_variables
                else get_default_minecraft_mods_installation_directory_path()
            )

            if not raw_minecraft_mods_installation_directory_path and not force_env_variables:
                extra_invalid_minecraft_mods_installation_directory_path_message = (
                    " (run a modded Minecraft version at least once "
                    "to create the `.minecraft/mods` directory)"
                )

        if not minecraft_mods_installation_directory_path.is_dir():
            INVALID_MINECRAFT_MODS_INSTALLATION_DIRECTORY_PATH_MESSAGE: Final[str] = (
                "MINECRAFT_MODS_INSTALLATION_DIRECTORY_PATH must be a valid path "
                "to your Minecraft mods installation directory"
                f"{extra_invalid_minecraft_mods_installation_directory_path_message}"
            )
            raise ImproperlyConfiguredError(
                INVALID_MINECRAFT_MODS_INSTALLATION_DIRECTORY_PATH_MESSAGE
            )

        self._settings["MINECRAFT_MODS_INSTALLATION_DIRECTORY_PATH"] = (
            minecraft_mods_installation_directory_path
        )

    def _setup_minecraft_versions_directory_path(self, *, minecraft_versions_directory_path: Path | None, force_env_variables: bool = False) -> None:  # noqa: E501
        if minecraft_versions_directory_path is None or force_env_variables:
            raw_minecraft_versions_directory_path: str = os.getenv(
                "MINECRAFT_VERSIONS_DIRECTORY_PATH",
                ""
            )

            minecraft_versions_directory_path = (
                Path(raw_minecraft_versions_directory_path)
                if raw_minecraft_versions_directory_path or force_env_variables
                else get_default_minecraft_versions_directory_path()
            )

        MINECRAFT_VERSIONS_DIRECTORY_PATH_IS_VALID: Final[bool] = bool(
            minecraft_versions_directory_path.is_dir()
            and minecraft_versions_directory_path_contains_a_valid_version(
                minecraft_versions_directory_path
            )
        )
        if not MINECRAFT_VERSIONS_DIRECTORY_PATH_IS_VALID:
            INVALID_MINECRAFT_VERSIONS_DIRECTORY_PATH_MESSAGE: Final[str] = (
                "MINECRAFT_VERSIONS_DIRECTORY_PATH must be a valid path "
                "to your Minecraft mods installation directory"
            )
            raise ImproperlyConfiguredError(
                INVALID_MINECRAFT_VERSIONS_DIRECTORY_PATH_MESSAGE
            )

        self._settings["MINECRAFT_VERSIONS_DIRECTORY_PATH"] = minecraft_versions_directory_path

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
                    "they will fail to be downloaded"
                )

                self._settings["CURSEFORGE_API_KEY"] = None
                return

            curseforge_api_key = raw_curseforge_api_key

        if not re.match(r"\A[A-Za-z0-9$/.]{60}\Z", curseforge_api_key):
            INVALID_CURSEFORGE_API_KEY_MESSAGE: Final[str] = (
                "CURSEFORGE_API_KEY must be a valid CurseForge API Key "
                "(see https://console.curseforge.com/?#/api-keys "
                "for how to generate CurseForge API keys)"
            )
            raise ImproperlyConfiguredError(INVALID_CURSEFORGE_API_KEY_MESSAGE)

        self._settings["CURSEFORGE_API_KEY"] = curseforge_api_key

    def _setup_filter_minecraft_version(self, *, filter_minecraft_version: str | None, force_env_variables: bool = False) -> None:  # noqa: E501
        if "MINECRAFT_VERSIONS_DIRECTORY_PATH" not in self._settings:
            INVALID_SETUP_ORDER_MESSAGE: Final[str] = (
                "Invalid setup order: MINECRAFT_VERSIONS_DIRECTORY_PATH must be set up "
                "before FILTER_MINECRAFT_VERSION is set up."
            )
            raise RuntimeError(INVALID_SETUP_ORDER_MESSAGE)

        if filter_minecraft_version is None or force_env_variables:
            raw_filter_minecraft_version: str = os.getenv(
                "FILTER_MINECRAFT_VERSION",
                ""
            )

            filter_minecraft_version = (
                raw_filter_minecraft_version
                if raw_filter_minecraft_version
                else get_latest_installed_minecraft_version(
                    minecraft_versions_directory_path=self._settings["MINECRAFT_VERSIONS_DIRECTORY_PATH"]  # type: ignore[arg-type]
                )
            )

        filter_minecraft_version_cleaner: BaseMod = BaseMod()
        filter_minecraft_version_cleaner.minecraft_version = filter_minecraft_version

        try:
            UnsanitisedMinecraftVersionValidator()(filter_minecraft_version)
            MinLengthValidator(2)(filter_minecraft_version)
            filter_minecraft_version_cleaner.clean()
        except ValidationError:
            INVALID_FILTER_MINECRAFT_VERSION_MESSAGE: Final[str] = (
                "FILTER_MINECRAFT_VERSION must be a valid Minecraft version "
                "(see https://minecraft.wiki/w/Version_formats#Release "
                "for an explanation about the Minecraft version format)"
            )
            raise ImproperlyConfiguredError(INVALID_FILTER_MINECRAFT_VERSION_MESSAGE) from None

        filter_minecraft_version = filter_minecraft_version_cleaner.minecraft_version

        MINECRAFT_VERSION_EXISTS: Final[bool] = any(
            minecraft_version_path_is_valid(minecraft_version_path)
            for minecraft_version_path
            in self._settings["MINECRAFT_VERSIONS_DIRECTORY_PATH"].iterdir()  # type: ignore
            if filter_minecraft_version.removesuffix(".0") in minecraft_version_path.name
        )
        if not MINECRAFT_VERSION_EXISTS:
            FILTER_MINECRAFT_VERSION_NOT_INSTALLED_MESSAGE: Final[str] = (
                "FILTER_MINECRAFT_VERSION must be a valid Minecraft version "
                "that has already been installed "
                "(to add mods to this minecraft version run Minecraft at the required version "
                "at least once)"
            )
            raise ImproperlyConfiguredError(
                FILTER_MINECRAFT_VERSION_NOT_INSTALLED_MESSAGE
            ) from None

        self._settings["FILTER_MINECRAFT_VERSION"] = filter_minecraft_version

    def _setup_filter_mod_loader(self, *, filter_mod_loader: ModLoader | None, force_env_variables: bool = False) -> None:  # noqa: E501
        if filter_mod_loader is None or force_env_variables:
            SETUP_ORDER_IS_INVALID: Final[bool] = bool(
                "FILTER_MINECRAFT_VERSION" not in self._settings
                or "MINECRAFT_VERSIONS_DIRECTORY_PATH" not in self._settings
            )
            if SETUP_ORDER_IS_INVALID:
                INVALID_SETUP_ORDER_MESSAGE: Final[str] = (
                    "Invalid setup order: "
                    "FILTER_MINECRAFT_VERSION and MINECRAFT_VERSIONS_DIRECTORY_PATH "
                    "must be set up before FILTER_MOD_LOADER is set up."
                )
                raise RuntimeError(INVALID_SETUP_ORDER_MESSAGE)

            raw_filter_mod_loader: str = os.getenv(
                "FILTER_MOD_LOADER",
                ""
            )

            if raw_filter_mod_loader:
                try:
                    filter_mod_loader = ModLoader(raw_filter_mod_loader.upper()[:2])
                except ValueError:
                    INVALID_FILTER_MOD_LOADER_MESSAGE: Final[str] = (
                        "FILTER_MOD_LOADER must be the name of a valid mod loader "
                        "(one of \"Forge\", \"Fabric\" or \"Quilt\")."
                    )
                    raise ImproperlyConfiguredError(
                        INVALID_FILTER_MOD_LOADER_MESSAGE
                    ) from None

            elif "FILTER_MINECRAFT_VERSION" in self._settings:
                filter_mod_loader = get_default_mod_loader(
                    minecraft_version=self._settings["FILTER_MINECRAFT_VERSION"],  # type: ignore[arg-type]
                    minecraft_versions_directory_path=self._settings["MINECRAFT_VERSIONS_DIRECTORY_PATH"]  # type: ignore[arg-type]
                )

        self._settings["FILTER_MOD_LOADER"] = filter_mod_loader

    def _setup_env_variables(self, *, minecraft_mods_installation_directory_path: Path | None, minecraft_versions_directory_path: Path | None, curseforge_api_key: str | None, filter_minecraft_version: str | None, filter_mod_loader: ModLoader | None, dry_run: bool = False, force_env_variables: bool = False, verbosity: int = 1) -> None:  # noqa: E501
        """
        Load environment values into the settings dictionary.

        Environment values are loaded from the .env file/the current environment variables and
        are only stored after the input values have been validated.
        """
        if self._is_env_variables_setup:
            logging.warning("Environment variables have already been set up.")
            return

        dotenv.load_dotenv()

        self._setup_logging(verbosity=verbosity, force_env_variables=force_env_variables)
        logging.debug("Successfully setup logging")

        self._setup_minecraft_mods_installation_directory_path(
            minecraft_mods_installation_directory_path=minecraft_mods_installation_directory_path,
            force_env_variables=force_env_variables
        )
        logging.debug(
            "Successfully setup Env variable: MINECRAFT_MODS_INSTALLATION_DIRECTORY_PATH"
        )

        self._setup_minecraft_versions_directory_path(
            minecraft_versions_directory_path=minecraft_versions_directory_path,
            force_env_variables=force_env_variables
        )
        logging.debug("Successfully setup Env variable: MINECRAFT_VERSIONS_DIRECTORY_PATH")

        self._setup_curseforge_api_key(
            curseforge_api_key=curseforge_api_key,
            force_env_variables=force_env_variables
        )
        logging.debug("Successfully setup Env variable: CURSEFORGE_API_KEY")

        self._setup_filter_minecraft_version(
            filter_minecraft_version=filter_minecraft_version,
            force_env_variables=force_env_variables
        )
        logging.debug("Successfully setup Env variable: FILTER_MINECRAFT_VERSION")

        self._setup_filter_mod_loader(
            filter_mod_loader=filter_mod_loader,
            force_env_variables=force_env_variables
        )
        logging.debug("Successfully setup Env variable: FILTER_MOD_LOADER")

        self._settings["DRY_RUN"] = dry_run
        logging.debug("Successfully setup Env variable: DRY_RUN")

        self._is_env_variables_setup = True


settings: Final[Settings] = Settings()


def run_setup(*, minecraft_mods_installation_directory_path: Path, minecraft_versions_directory_path: Path, curseforge_api_key: str, filter_minecraft_version: str, filter_mod_loader: ModLoader, dry_run: bool, force_env_variables: bool, verbosity: int) -> None:  # noqa: E501
    """Execute the setup functions required, before other modules can be run."""
    with SuppressTraceback(verbosity):
        with SuppressStdOutAndStdErr(verbosity):
            # noinspection PyProtectedMember
            settings._setup_env_variables(  # noqa: SLF001
                minecraft_mods_installation_directory_path=minecraft_mods_installation_directory_path,
                minecraft_versions_directory_path=minecraft_versions_directory_path,
                curseforge_api_key=curseforge_api_key,
                filter_minecraft_version=filter_minecraft_version,
                filter_mod_loader=filter_mod_loader,
                dry_run=dry_run,
                force_env_variables=force_env_variables,
                verbosity=verbosity
            )

        logging.debug("Begin database setup")

        with SuppressStdOutAndStdErr(verbosity - 2):
            management.call_command("migrate")

        logging.debug("Database setup completed")


IS_ENV_VARIABLES_SETUP: bool


def __getattr__(item: str) -> object:
    if item == "IS_ENV_VARIABLES_SETUP":  # noqa: PLR2004
        # noinspection PyProtectedMember
        return settings._is_env_variables_setup  # noqa: SLF001

    MODULE_ATTRIBUTE_ERROR_MESSAGE: Final[str] = (
        f"module {__name__!r} has no attribute {item!r}"
    )
    raise AttributeError(MODULE_ATTRIBUTE_ERROR_MESSAGE)
