"""
Console script wrapper for Minecraft Mod Downloader.

This script performs argument parsing & sends a return code back to the console.
"""

from collections.abc import Sequence

__all__: Sequence[str] = ("run",)

from django.core import management

from minecraft_mod_downloader import config
from minecraft_mod_downloader.utils import SuppressTraceback


def run(argv: Sequence[str] | None = None) -> int:
    """Run the Minecraft Mod Downloader tool as a CLI tool with argument parsing."""

    with SuppressTraceback():
        config.setup_env_variables()
        config.setup_django()
        management.call_command("migrate")

    return 0
