from collections.abc import Sequence

__all__: Sequence[str] = (
    "BaseMod",
    "SimpleMod",
    "CustomSourceMod",
    "APISourceMod",
    "ModTag",
    "MinecraftVersionValidator"
)

from minecraft_mod_downloader import config

if config.IS_DJANGO_SETUP:
    # noinspection PyProtectedMember
    from minecraft_mod_downloader.models._mem_db_core.models import (
        APISourceMod,
        BaseMod,
        CustomSourceMod,
        MinecraftVersionValidator,
        ModTag,
        SimpleMod,
    )
