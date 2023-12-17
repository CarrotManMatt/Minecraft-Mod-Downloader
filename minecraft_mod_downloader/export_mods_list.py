from collections.abc import Sequence

__all__: Sequence[str] = ("can_export_as_csv", "export_mods_list")

from pathlib import Path
import logging

from django.core import management

from minecraft_mod_downloader.config import settings
from minecraft_mod_downloader.exceptions import ImproperlyConfiguredError
from minecraft_mod_downloader.models import BaseMod, SimpleMod


def can_export_as_csv(*, export_file_path: Path) -> bool:
    if export_file_path.suffix.lower() == ".csv":
        if BaseMod.objects.count() == SimpleMod.objects.count():
            return True

        raise ImproperlyConfiguredError(
            "Can't export as CSV file when DetailedMod objects have been loaded"
        )

    return False


def export_mods_list_as_csv(*, export_file_path: Path) -> None:
    if not settings["DRY_RUN"]:
        export_file_path.parent.mkdir(exist_ok=True, parents=True)
        export_file_path.write_text(
            "\n".join(SimpleMod.objects.values_list("_unique_identifier", flat=True)) + "\n"
        )

    logging.info(
        f"Successfully wrote {SimpleMod.objects.count()} SimpleMod objects "
        f"to `{export_file_path}`"
    )


def export_mods_list_as_json(*, export_file_path: Path) -> None:
    export_file_path.parent.mkdir(exist_ok=True, parents=True)

    if not settings["DRY_RUN"]:
        management.call_command(
            "dumpdata",
            "_mem_db_core",
            format="json",
            indent=4,
            output=export_file_path,
            natural_foreign=True,
            natural_primary=True
        )

    logging.info(
        f"Successfully wrote {BaseMod.objects.count()} mod objects to `{export_file_path}`"
    )


def export_mods_list(*, export_file_path: Path) -> None:
    if can_export_as_csv(export_file_path=export_file_path):
        export_mods_list_as_csv(export_file_path=export_file_path)
        return

    if export_file_path.suffix.lower() != ".json":
        raise ImproperlyConfiguredError(
            "DetailedMod objects can be exported only into a JSON file"
        )

    export_mods_list_as_json(export_file_path=export_file_path)
