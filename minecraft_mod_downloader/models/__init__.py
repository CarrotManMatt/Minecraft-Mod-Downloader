import os
from collections.abc import Sequence

import django

__all__: Sequence[str] = (
    "BaseMod",
    "SimpleMod",
    "CustomSourceMod",
    "APISourceMod",
    "ModLoader",
    "ModTag",
    "MinecraftVersionValidator",
    "UnsanitisedMinecraftVersionValidator"
)
os.environ["DJANGO_SETTINGS_MODULE"] = "minecraft_mod_downloader.models._settings"
django.setup()

# noinspection PyProtectedMember
from minecraft_mod_downloader.models._mem_db_core.models import (
    APISourceMod,
    BaseMod,
    CustomSourceMod,
    MinecraftVersionValidator,
    UnsanitisedMinecraftVersionValidator,
    ModTag,
    SimpleMod,
    ModLoader
)
