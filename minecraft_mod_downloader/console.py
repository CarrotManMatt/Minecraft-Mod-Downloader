"""
Console script wrapper for Minecraft Mod Downloader.

This script performs argument parsing & sends a return code back to the console.
"""

from collections.abc import Sequence
import os
import django

__all__: Sequence[str] = ("run",)
os.environ["DJANGO_SETTINGS_MODULE"] = "minecraft_mod_downloader.models._settings"
django.setup()

import argparse
from argparse import ArgumentParser, Namespace
from typing import TYPE_CHECKING

from django.core import management

from minecraft_mod_downloader import config
from minecraft_mod_downloader.utils import SuppressStdOutAndStdErr, SuppressTraceback
from minecraft_mod_downloader import parse_mods_list

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from argparse import _MutuallyExclusiveGroup as MutuallyExclusiveGroup


def set_up_arg_parser() -> ArgumentParser:
    # TODO: Named groups
    arg_parser: ArgumentParser = ArgumentParser(
        description=(
            "Download the given list of Minecraft mods into your installation mod directory"
        ),
        usage=(
            "%(prog)s [-h] [-D] [-E] [-q | -v | -vv | -vvv] "
            "[--mods-list-file MODS_LIST_FILE | --mods-list [MODS_LIST ...]] "
            "[--minecraft-installation-directory MINECRAFT_INSTALLATION_DIRECTORY] "
            "[--curseforge-api-key CURSEFORGE_API_KEY]"
        )
    )

    mods_list_args_group: MutuallyExclusiveGroup = arg_parser.add_mutually_exclusive_group()
    mods_list_args_group.add_argument(
        "--mods-list-file",
        type=argparse.FileType("r"),
        help=(
            "A file containing your mods list. Mutually exclusive with `--mods-list`"
        )
    )
    mods_list_args_group.add_argument(
        "--mods-list",
        nargs="*",
        help=(
            "A manually entered list of mods to download. "
            "Mutually exclusive with `--mods-list-file-path`"
        )
    )

    arg_parser.add_argument(
        "--minecraft-installation-directory",
        dest="minecraft_installation_directory_path",
        help=(
            "Path to the directory containing your minecraft installation & "
            "mods folder within that"
        )
    )
    arg_parser.add_argument(
        "--curseforge-api-key",
        help=(
            "The API key to use to authenticate, "
            "when downloading mods from the CurseForge API. "
            "If your mods list does not contain any mods "
            "to be downloaded from the CurseForge API, a key is not required."
        )
    )

    arg_parser.add_argument(
        "--filter-minecraft-version",
        help=(
            "The Minecraft version to download compatible mods for. "
            "If this option is not provided, the latest version "
            "from your MINECRAFT_INSTALLATION_DIRECTORY will be used."
        )
    )
    arg_parser.add_argument(
        "--filter-mod-loader",
        help=(
            "The mod loader to download compatible mods for. "
            "If this option is not provided, "
            "the mod loader of the profile with the latest version will be used"
        )
    )

    arg_parser.add_argument(
        "-D",
        "--dry-run",
        action="store_true",
        help=(
            "Output the operations but do not execute anything. Implicitly enables `--verbose`"
        )
    )
    arg_parser.add_argument(
        "-E",
        "--force-env-variables",
        action="store_true",
        help=(
            "Force the use of the values stored as environment variables, "
            "overriding any supplied command-line arguments"
        )
    )

    verbosity_args_group: MutuallyExclusiveGroup = arg_parser.add_mutually_exclusive_group()
    verbosity_args_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Do not output any messages. Mutually exclusive with `--verbose`"
    )
    verbosity_args_group.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbosity",
        help="Increase the verbosity of messages. Mutually exclusive with `--quiet`"
    )

    return arg_parser


def run(argv: Sequence[str] | None = None) -> int:
    """Run the Minecraft Mod Downloader tool as a CLI tool with argument parsing."""

    arg_parser: ArgumentParser = set_up_arg_parser()

    parsed_args: Namespace = arg_parser.parse_args(argv)

    verbosity: int = 0 if parsed_args.quiet else parsed_args.verbosity + 1

    if parsed_args.dry_run:
        if parsed_args.quiet:
            arg_parser.error("argument -q/--quiet: not allowed with argument -D/--dry-run")
            return 2

        if verbosity <= 1:
            verbosity = 1

    with SuppressTraceback(verbosity):
        with SuppressStdOutAndStdErr(verbosity):
            config.setup_env_variables(
                minecraft_installation_directory_path=parsed_args.minecraft_installation_directory_path,
                curseforge_api_key=parsed_args.curseforge_api_key,
                filter_minecraft_version=parsed_args.filter_minecraft_version,
                filter_mod_loader=parsed_args.filter_mod_loader,
                dry_run=parsed_args.dry_run,
                force_env_variables=parsed_args.force_env_variables,
                verbosity=verbosity
            )
            config.setup_django()

        with SuppressStdOutAndStdErr(verbosity - 1):
            management.call_command("migrate")

        with SuppressStdOutAndStdErr(verbosity):
            parse_mods_list.setup_raw_mods_list(
                mods_list_file=parsed_args.mods_list_file,
                mods_list=",".join(parsed_args.mods_list),
                force_env_variables=parsed_args.force_env_variables
            )

    return 0
