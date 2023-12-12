"""A Python helper script to load a set of mods from a local mods-list."""

from collections.abc import Sequence

__all__: Sequence[str] = ("run",)

from minecraft_mod_downloader.console import run
