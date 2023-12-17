"""Configurations to make _mem_db_core app ready to import into _settings.py."""

from collections.abc import Sequence

__all__: Sequence[str] = ("MemDBCoreConfig",)

from django.apps import AppConfig


class MemDBCoreConfig(AppConfig):
    """
    Contains all the configuration required for the _mem_db_core app.

    Extends the django.apps.AppConfig class which contains the methods to initialise the app,
    apply migrations, etc.
    """

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "minecraft_mod_downloader.models._mem_db_core"

    def ready(self):
        from minecraft_mod_downloader.models._mem_db_core import signals
