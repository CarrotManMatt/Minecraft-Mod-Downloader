from collections.abc import Sequence

__all__: Sequence[str] = ("download_mods",)

import hashlib
import string
from datetime import datetime
import random
import logging
from collections.abc import Iterable, Mapping, AsyncIterable
from io import BytesIO
from typing import Final, TypeAlias
import asyncio
from aiopath import AsyncPath
from asgiref.sync import sync_to_async
from django.db.models import QuerySet
from httpx import AsyncClient

from minecraft_mod_downloader.config import settings
from minecraft_mod_downloader.exceptions import ImproperlyConfiguredError, InvalidCalculatedFileHash, ModRequiresManualDownloadError, NoCompatibleModVersionFoundOnlineError
from minecraft_mod_downloader.models import APISourceMod, DetailedMod, CustomSourceMod

ModrinthModVersionDetails: TypeAlias = Mapping[
    str,
    (
        str
        | bool
        | int
        | None
        | Sequence[str]
        | Sequence[Mapping[str, str | None]]
        | Sequence[Mapping[str, str | None | bool | int | Mapping[str, str]]]
    )
]
CurseForgeProjectDetails: TypeAlias = Mapping[
    str,
    (
        str
        | bool
        | int
        | Mapping[str, str]
        | Sequence[Mapping[str, str | int | bool]]
        | Sequence[Mapping[str, str | int | bool | Sequence[Mapping[str, str | int]]]]
    )
]
CurseForgeModFileDetails: TypeAlias = Mapping[
    str,
    (
        str
        | bool
        | int
        | Sequence[str]
        | Sequence[Mapping[str, str | int]]
    )
]


def _get_major_minecraft_version(minecraft_version: str) -> str:
    split_minecraft_version: Sequence[str] = minecraft_version.split(".")
    return split_minecraft_version[0] + "." + split_minecraft_version[1]


def get_fallback_minecraft_versions(original_minecraft_version: str) -> Iterable[str]:
    return (
        {original_minecraft_version}
        | {
            f"{_get_major_minecraft_version(original_minecraft_version)}.{num}"
            for num in
            range(int(original_minecraft_version.rsplit(".", maxsplit=1)[-1]) - 1, 0, -1)
        }
        | {_get_major_minecraft_version(original_minecraft_version)}
    )


@sync_to_async
def _get_api_source_mod_from_mod(mod: DetailedMod) -> APISourceMod:
    return mod.apisourcemod


@sync_to_async
def _get_custom_source_mod_from_mod(mod: DetailedMod) -> CustomSourceMod:
    return mod.customsourcemod


async def _download_mod_from_modrinth(mod: APISourceMod, http_client: AsyncClient) -> None:
    FALLBACK_MINECRAFT_VERSIONS: Final[Iterable[str]] = get_fallback_minecraft_versions(
        mod.minecraft_version
    )

    minecraft_version: str
    for minecraft_version in FALLBACK_MINECRAFT_VERSIONS:
        logging.debug(
            f"{mod} - Testing to see if an online mod version exists "
            f"for Minecraft {minecraft_version}"
        )

        latest_mod_versions_list: Iterable[ModrinthModVersionDetails] = (
            random.choice(
                (
                    (
                        {
                            "id": mod.version_id,
                            "project_id": mod.api_mod_id,
                            "author_id": "99999",
                            "featured": random.choice((True, False)),
                            "name": mod.name,
                            "version_number": "1.0.1",
                            "changelog": "Empty dry-run changelog.",
                            "changelog_url": None,
                            "date_published": (
                                f"{datetime.fromtimestamp(0).isoformat()}.000000Z"
                            ),
                            "downloads": 9999,
                            "version_type": "release",
                            "status": "listed",
                            "requested_status": None,
                            "dependencies": (),
                            "game_versions": list(FALLBACK_MINECRAFT_VERSIONS),
                            "loaders": mod.get_formatted_mod_loaders().replace(
                                "\"",
                                ""
                            ).split(","),
                            "files": (
                                {
                                    "hashes": {
                                        "sha512": (
                                            "d42ff897da68cf9aa6e3bbeea717f0096ae3143016936cc5e"
                                            "0971abc13ae32ddb91cccd8f04ff5359e0d7d1f575ffb80ea"
                                            "78165ae0c0fd9014b56c9e49cae104"
                                        ),
                                        "sha1": "09e49f48d2c432b1b0bf60ba4ff93046f2cc4ae7"
                                    },
                                    "url": (
                                        f"https://cdn.modrinth.com/data/{mod.api_mod_id}/"
                                        f"versions/{mod.version_id}/{mod.filename}"
                                    ),
                                    "filename": mod.filename,
                                    "primary": True,
                                    "size": 99999,
                                    "file_type": None
                                },
                            )
                        },
                    ),
                    (
                        {
                            "id": "99999" if mod.version_id != "99999" else "88888",
                            "project_id": mod.api_mod_id,
                            "author_id": "99999",
                            "featured": random.choice((True, False)),
                            "name": mod.name,
                            "version_number": (
                                "1.0.1" if "1.0.1" not in mod.filename else "2.0.1"
                            ),
                            "changelog": "Empty dry-run changelog.",
                            "changelog_url": None,
                            "date_published": (
                                f"{datetime.fromtimestamp(0).isoformat()}.000000Z"
                            ),
                            "downloads": 9999,
                            "version_type": "release",
                            "status": "listed",
                            "requested_status": None,
                            "dependencies": (),
                            "game_versions": list(FALLBACK_MINECRAFT_VERSIONS),
                            "loaders": mod.get_formatted_mod_loaders().replace(
                                "\"",
                                ""
                            ).split(","),
                            "files": (
                                {
                                    "hashes": {
                                        "sha512": (
                                            "d42ff897da68cf9aa6e3bbeea717f0096ae3143016936cc5e"
                                            "0971abc13ae32ddb91cccd8f04ff5359e0d7d1f575ffb80ea"
                                            "78165ae0c0fd9014b56c9e49cae104"
                                        ),
                                        "sha1": "09e49f48d2c432b1b0bf60ba4ff93046f2cc4ae7"
                                    },
                                    "url": (
                                        f"https://cdn.modrinth.com/data/{mod.api_mod_id}/"
                                        f"versions/{
                                            "99999" if mod.version_id != "99999" else "88888"
                                        }/"
                                        f"{mod.filename.strip("." + string.digits + "jar")}{
                                            "1.0.1" if "1.0.1" not in mod.filename else "2.0.1"
                                        }.jar"
                                    ),
                                    "filename": (
                                        f"{mod.filename.strip("." + string.digits + "jar")}{
                                            "1.0.1" if "1.0.1" not in mod.filename else "2.0.1"
                                        }.jar"
                                    ),
                                    "primary": True,
                                    "size": 99999,
                                    "file_type": None
                                },
                            )
                        },
                    ),
                    ()
                )
            )
            if settings["DRY_RUN"]
            else sorted(
                (
                    await http_client.get(
                        f"https://api.modrinth.com/v2/project/{mod.api_mod_id}/version?"
                        f"loaders=[{mod.get_formatted_mod_loaders()}]"
                        f"&game_versions=[\"{minecraft_version}\"]"
                    )
                ).json(),
                key=lambda _mod: _mod["version_number"],
                reverse=True
            )
        )

        if latest_mod_versions_list:
            logging.debug(
                f"{mod} - Online mod version exists for Minecraft {minecraft_version}"
            )
            break

        logging.debug(
            f"{mod} - No online mod version exists for Minecraft {minecraft_version}"
        )

    else:
        raise NoCompatibleModVersionFoundOnlineError(mod=mod)

    latest_mod_version_details: ModrinthModVersionDetails = next(
        iter(latest_mod_versions_list)
    )

    # noinspection PyTypeChecker
    new_local_mod_file_path: AsyncPath = (
        AsyncPath(settings["MINECRAFT_MODS_INSTALLATION_DIRECTORY_PATH"])
        / latest_mod_version_details["files"][0]["filename"]
    )

    # noinspection PyArgumentList,PyTypeChecker
    LOCAL_MOD_FILE_IS_UP_TO_DATE: Final[bool] = bool(
        mod.version_id == latest_mod_version_details["id"]
        and mod.filename == latest_mod_version_details["files"][0]["filename"]
        and await new_local_mod_file_path.exists()
    )
    if LOCAL_MOD_FILE_IS_UP_TO_DATE:
        logging.info(f"{mod} - Local mod file is up to date")
        return

    logging.info(f"{mod} - Update, compared to local mod file, found!")

    logging.debug(f"{mod} - Attempting to remove local old-version mod file")
    try:
        # noinspection PyArgumentList
        await (
            AsyncPath(settings["MINECRAFT_MODS_INSTALLATION_DIRECTORY_PATH"]) / mod.filename
        ).unlink()
    except FileNotFoundError:
        logging.debug(f"{mod} - No local old-version mod file found")

    await mod.aupdate(version_id=str(latest_mod_version_details["id"]))

    logging.debug(f"{mod} - Downloading new version")

    hash_exception: InvalidCalculatedFileHash | None = None

    if not settings["DRY_RUN"]:
        # noinspection PyTypeChecker
        new_local_mod_file: BytesIO = BytesIO(
            (await http_client.get(latest_mod_version_details["files"][0]["url"])).content
        )

        # noinspection PyTypeChecker
        hashes_are_valid = bool(
            (
                hashlib.sha1(new_local_mod_file.getbuffer()).hexdigest()
                == latest_mod_version_details["files"][0]["hashes"]["sha1"]
            )
            and (
                hashlib.sha512(new_local_mod_file.getbuffer()).hexdigest()
                == latest_mod_version_details["files"][0]["hashes"]["sha512"]
            )
        )
        if hashes_are_valid:
            await new_local_mod_file_path.write_bytes(new_local_mod_file.getvalue())
        else:
            # noinspection PyTypeChecker
            hash_exception = InvalidCalculatedFileHash(
                expected_hash={
                    latest_mod_version_details["files"][0]["hashes"]["sha1"],
                    latest_mod_version_details["files"][0]["hashes"]["sha512"]
                },
                calculated_hash=hashlib.sha512(new_local_mod_file.getbuffer()).hexdigest()
            )

    # noinspection PyTypeChecker
    await mod.aupdate(filename=latest_mod_version_details["files"][0]["filename"])

    if hash_exception is not None:
        raise hash_exception from None


async def _download_mod_from_curseforge(mod: APISourceMod, http_client: AsyncClient) -> None:
    FALLBACK_MINECRAFT_VERSIONS: Final[Iterable[str]] = get_fallback_minecraft_versions(
        mod.minecraft_version
    )

    if settings["DRY_RUN"]:
        raise NotImplementedError

    project_details: CurseForgeProjectDetails = (
        await http_client.get(
            f"https://api.curseforge.com/v1/mods/{mod.api_mod_id}/",
            headers={
                "Accept": "application/json",
                "x-api-key": settings["CURSEFORGE_API_KEY"]
            }
        )
    ).json()["data"]

    minecraft_version: str
    for minecraft_version in FALLBACK_MINECRAFT_VERSIONS:
        logging.debug(
            f"{mod} - Testing to see if an online mod version exists "
            f"for Minecraft {minecraft_version}"
        )

        try:
            # noinspection PyTypeChecker
            latest_online_mod_version_details: Mapping[str, str | int] = next(
                online_file_details
                for online_file_details in project_details["latestFilesIndexes"]
                if online_file_details["gameVersion"] == minecraft_version
            )

        except StopIteration:
            logging.debug(
                f"{mod} - No online mod version exists for Minecraft {minecraft_version}"
            )
            continue

        else:
            logging.debug(
                f"{mod} - Online mod version exists for Minecraft {minecraft_version}"
            )
            break

    else:
        raise NoCompatibleModVersionFoundOnlineError(mod=mod)

    # noinspection PyTypeChecker
    new_local_mod_file_path: AsyncPath = (
        AsyncPath(settings["MINECRAFT_MODS_INSTALLATION_DIRECTORY_PATH"])
        / latest_online_mod_version_details["filename"]
    )

    # noinspection PyArgumentList,PyTypeChecker
    LOCAL_MOD_FILE_IS_UP_TO_DATE: Final[bool] = bool(
        mod.version_id == latest_online_mod_version_details["fileId"]
        and mod.filename == latest_online_mod_version_details["filename"]
        and await new_local_mod_file_path.exists()
    )
    if LOCAL_MOD_FILE_IS_UP_TO_DATE:
        logging.info(f"{mod} - Local mod file is up to date")
        return

    logging.info(f"{mod} - Update, compared to local mod file, found!")

    logging.debug(f"{mod} - Attempting to remove local old-version mod file")
    try:
        # noinspection PyArgumentList
        await (
            AsyncPath(settings["MINECRAFT_MODS_INSTALLATION_DIRECTORY_PATH"]) / mod.filename
        ).unlink()
    except FileNotFoundError:
        logging.debug(f"{mod} - No local old-version mod file found")

    await mod.aupdate(version_id=str(latest_online_mod_version_details["fileId"]))

    logging.debug(f"{mod} - Downloading new version")

    hash_exception: InvalidCalculatedFileHash | None = None

    if not settings["DRY_RUN"]:
        try:
            # noinspection PyTypeChecker
            latest_online_mod_file_details: CurseForgeModFileDetails = next(
                latest_file
                for latest_file
                in project_details["latestFiles"]
                if latest_file["id"] == mod.version_id
            )
        except StopIteration:
            latest_online_mod_file_details: CurseForgeModFileDetails = (
                await http_client.get(
                    (
                        f"https://api.curseforge.com/v1/mods/{mod.api_mod_id}/"
                        f"files/{mod.version_id}"
                    ),
                    headers={
                        "Accept": "application/json",
                        "x-api-key": settings["CURSEFORGE_API_KEY"]
                    }
                )
            ).json()["data"]

        # noinspection PyTypeChecker
        new_local_mod_file: BytesIO = BytesIO(
            (await http_client.get(latest_online_mod_file_details["downloadUrl"])).content
        )

        # noinspection PyTypeChecker
        HASHES_ARE_VALID: Final[bool] = any(
            bool(
                hashlib.md5(new_local_mod_file.getbuffer()).hexdigest()
                == expected_hash["value"]
            )
            for expected_hash
            in latest_online_mod_file_details["hashes"]
        )
        if HASHES_ARE_VALID:
            await new_local_mod_file_path.write_bytes(new_local_mod_file.getvalue())
        else:
            # noinspection PyTypeChecker
            hash_exception = InvalidCalculatedFileHash(
                expected_hash={
                    expected_hash["value"]
                    for expected_hash
                    in latest_online_mod_file_details["hashes"]
                },
                calculated_hash=hashlib.md5(new_local_mod_file.getbuffer()).hexdigest()
            )

    # noinspection PyTypeChecker
    await mod.aupdate(filename=latest_online_mod_version_details["filename"])

    if hash_exception is not None:
        raise hash_exception from None


async def download_mod_from_api(mod: APISourceMod, http_client: AsyncClient) -> None:
    logging.debug(
        f"{mod} - Getting latest version online from {mod.get_mod_loader_display()} API"
    )

    if mod.api_source == APISourceMod.APISource.MODRINTH:
        await _download_mod_from_modrinth(mod, http_client)
        return

    await _download_mod_from_curseforge(mod, http_client)


# noinspection PyUnusedLocal
async def download_mod_from_custom_source(mod: CustomSourceMod, http_client: AsyncClient) -> None:
    raise ModRequiresManualDownloadError(mod=mod)


async def download_single_mod(mod: DetailedMod, http_client: AsyncClient) -> None:
    logging.debug(f"{mod} - Begin checking")

    try:
        await download_mod_from_api(await _get_api_source_mod_from_mod(mod), http_client)
    except APISourceMod.DoesNotExist:
        try:
            await download_mod_from_custom_source(
                await _get_custom_source_mod_from_mod(mod),
                http_client
            )
        except CustomSourceMod.DoesNotExist:
            UNKNOWN_MOD_SOURCE_MESSAGE: str = (
                f"DetailedMod object \"{mod}\" cannot be downloaded, "
                "because there is no implementation for how to download mods "
                "from the given source"
            )
            raise NotImplementedError(UNKNOWN_MOD_SOURCE_MESSAGE)

    logging.debug(f"{mod} - Checking complete")


async def _download_mods(all_mods_to_install: AsyncIterable[DetailedMod]) -> tuple[BaseException | None]:
    http_client: AsyncClient
    async with AsyncClient() as http_client:
        return (
            await asyncio.gather(
                *[download_single_mod(mod, http_client) async for mod in all_mods_to_install],
                return_exceptions=True
            )
        )


def download_mods() -> None:
    ALL_MODS_TO_INSTALL: Final[QuerySet[DetailedMod]] = DetailedMod.objects.filter(
        disabled=False,
        minecraft_version=settings["FILTER_MINECRAFT_VERSION"],
        mod_loader=settings["FILTER_MOD_LOADER"]
    )

    CAN_DOWNLOAD_FROM_CURSEFORGE: Final[bool] = bool(
        not APISourceMod.objects.filter(
            pk__in=ALL_MODS_TO_INSTALL,
            api_source=APISourceMod.APISource.CURSEFORGE
        ).exists()
        or settings["CURSEFORGE_API_KEY"] is not None
    )
    if not CAN_DOWNLOAD_FROM_CURSEFORGE:
        raise ImproperlyConfiguredError(
            "Cannot check for updates/download mods from the CurseForge API, "
            "if no CURSEFORGE_API_KEY is provided"
        ) from None

    logging.info(f"Checking for updates to {ALL_MODS_TO_INSTALL.count()} mods")

    if not ALL_MODS_TO_INSTALL.exists():
        logging.error(
            "None of the mods in your mods-list match "
            f"the requested Minecraft version: {settings["FILTER_MINECRAFT_VERSION"]} & "
            f"mod-loader: {settings["FILTER_MOD_LOADER"].label}"
        )
        return

    MOD_DOWNLOAD_RESULTS: Final[Iterable[BaseException | None]] = asyncio.run(
        _download_mods(all_mods_to_install=ALL_MODS_TO_INSTALL)
    )

    download_result: BaseException | None
    for download_result in MOD_DOWNLOAD_RESULTS:
        if download_result is None:
            continue

        if isinstance(download_result, NoCompatibleModVersionFoundOnlineError):
            logging.error(download_result.message)
            input("Press Enter to continue...")

            continue

        if isinstance(download_result, ModRequiresManualDownloadError):
            logging.warning(f"Mods from custom sources must be downloaded manually")

            logging.error(
                f"Download the latest version of {download_result.mod} "
                f"from {download_result.mod.download_url}"
            )
            logging.info(f"Current mod version: {download_result.mod.version_id}")
            input("Press Enter to continue...")

            continue

        raise download_result from download_result

    logging.debug("All mods are now at their latest versions")
