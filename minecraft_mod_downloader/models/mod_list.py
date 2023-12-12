import itertools
from collections.abc import Sequence

__All__: Sequence[str] = ("ModList",)

from collections.abc import Iterable, Iterator, Mapping
from typing import Any, Self

from minecraft_mod_downloader.models.mod import BaseMod

# TODO use Django Queryset
class ModList(set):
    """"""
