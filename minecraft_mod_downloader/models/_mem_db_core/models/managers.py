from collections.abc import Sequence

__all__: Sequence[str] = ("ModTagManager",)

from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from minecraft_mod_downloader.models import ModTag


class ModTagManager(models.Manager):
    def get_by_natural_key(self, name: str) -> "ModTag":
        return self.get(name=name)
