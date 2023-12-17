from collections.abc import Sequence

__all__: Sequence[str] = ("check_for_database_changes",)

import logging
from typing import Final

from minecraft_mod_downloader.config import settings


def check_for_database_changes(export_file_path_was_empty: bool) -> None:
    SEND_DATABASE_CHANGES_WARNING: Final[bool] = bool(
        settings["DATABASE_HAS_CHANGED"]
        and not settings["DRY_RUN"]
        and export_file_path_was_empty
    )
    if SEND_DATABASE_CHANGES_WARNING:
        logging.warning(
            "Changes were made to the internally referenced mods-list "
            "because new mod versions were found. "
            "To save these changes & prevent re-downloading mod files, "
            "use the `--export` CLI argument to define a file "
            "to export the internally referenced mods-list"
        )
