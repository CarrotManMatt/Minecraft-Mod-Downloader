"""Utility classes & functions provided for use across the whole of the project."""

from collections.abc import Sequence

__all__: Sequence[str] = ("SuppressTraceback", "SuppressStdOutAndStdErr")

from minecraft_mod_downloader.utils.suppress_traceback import SuppressTraceback
from minecraft_mod_downloader.utils.suppress_stdoutand_stderr import SuppressStdOutAndStdErr
