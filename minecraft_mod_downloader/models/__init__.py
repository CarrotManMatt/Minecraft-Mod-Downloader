from collections.abc import Sequence

__all__: Sequence[str] = (
    "BaseMod",
    "SimpleMod",
    "CustomSourceMod",
    "APISourceMod",
    "ModTag",
    "MinecraftVersionValidator"
)

from minecraft_mod_downloader.config import settings

if settings.is_django_setup:
    # noinspection PyProtectedMember
    from minecraft_mod_downloader.models._mem_db_core.models import (
        BaseMod,
        SimpleMod,
        CustomSourceMod,
        APISourceMod,
        ModTag,
        MinecraftVersionValidator
    )
