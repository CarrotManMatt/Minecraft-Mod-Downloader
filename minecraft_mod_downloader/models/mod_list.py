import itertools
from collections.abc import Sequence

__All__: Sequence[str] = ("ModList",)

from collections.abc import Iterable, Iterator, Mapping
from typing import Self

from minecraft_mod_downloader.models.mod import BaseMod


class ModList(set):
    @classmethod
    def _from_mutable_mapping(cls, mutable_mapping: Mapping[str, BaseMod]) -> Self:
        new_mod_list: Self = cls(())
        new_mod_list._mods = dict(mutable_mapping)
        return new_mod_list

    # noinspection PyMissingConstructor
    def __init__(self, mods: Iterable[BaseMod]) -> None:
        self._mods: dict[str, BaseMod] = {mod.get_unique_identifier(): mod for mod in mods}

    def __contains__(self, mod: BaseMod) -> bool:
        return mod.get_unique_identifier() in self._mods

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented

        return (
            all(
                mod_unique_identifier in other._mods
                for mod_unique_identifier
                in self._mods
            )
            and all(
                mod_unique_identifier in self._mods
                for mod_unique_identifier in
                other._mods
            )
        )

    def __le__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented

        return all(
            mod_unique_identifier in other._mods
            for mod_unique_identifier
            in self._mods
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented

        return (
            all(
                mod_unique_identifier in other._mods
                for mod_unique_identifier
                in self._mods
            )
            and self != other
        )

    def __or__(self, *others: object) -> Self:
        raise NotImplementedError  # TODO

    def __ior__(self, *others: object) -> Self:
        raise NotImplementedError  # TODO

    def __and__(self, *others: object) -> Self:
        raise NotImplementedError  # TODO

    def __iand__(self, *others: object) -> Self:
        raise NotImplementedError  # TODO

    def __sub__(self, *others: object) -> Self:
        raise NotImplementedError  # TODO

    def __isub__(self, *others: object) -> Self:
        raise NotImplementedError  # TODO

    def __xor__(self, other: object) -> Self:
        raise NotImplementedError  # TODO

    def __ixor__(self, other: object) -> Self:
        raise NotImplementedError  # TODO

    def __iter__(self) -> Iterator[BaseMod]:
        return iter(self.values())

    def __len__(self) -> int:
        return len(self._mods)

    def __str__(self) -> str:
        return f"""{{{", ".join(str(mod) for mod in self)}}}"""

    def __repr__(self) -> str:
        return f"""{{{", ".join(repr(mod) for mod in self)}}}"""

    def add(self, mod: BaseMod) -> None:
        mod_unique_identifier: str = mod.get_unique_identifier()
        if mod_unique_identifier not in self._mods:
            self._mods[mod_unique_identifier] = mod

    def clear(self) -> None:
        self._mods.clear()

    def copy(self) -> Self:
        return ModList._from_mutable_mapping(self._mods.copy())

    def difference(self, *other_mod_lists: Iterable[BaseMod]) -> Self:
        if all(isinstance(other_mod_list, ModList) for other_mod_list in other_mod_lists):
            return self.__sub__(*other_mod_lists)

        new_mod_list: ModList = ModList(())

        mod: BaseMod
        for mod in self:
            if mod not in set(itertools.chain(*other_mod_lists)):
                new_mod_list._mods[mod.get_unique_identifier()] = mod

        return new_mod_list

    def difference_update(self, *other_mod_lists: Iterable[BaseMod]) -> None:
        if all(isinstance(other_mod_list, ModList) for other_mod_list in other_mod_lists):
            self.__isub__(*other_mod_lists)

        mod: BaseMod
        for mod in itertools.chain(other_mod_lists):
            mod_unique_identifier: str = mod.get_unique_identifier()
            if mod_unique_identifier in self._mods:
                self._mods.pop(mod_unique_identifier)

    def discard(self, mod: BaseMod) -> None:
        self._mods.pop(mod.get_unique_identifier(), None)

    def intersection(self, *other_mod_lists: Iterable[BaseMod]) -> Self:
        new_mod_list: ModList = ModList(())

        next_mod_list: Iterable[BaseMod]
        next_mod_list, *other_mod_lists = other_mod_lists

        if isinstance(next_mod_list, ModList):
            new_mod_list = new_mod_list.__and__(next_mod_list)
        else:
            mod: BaseMod
            for mod in self:
                if mod in next_mod_list:
                    new_mod_list._mods[mod.get_unique_identifier()] = mod

        return new_mod_list.intersection(*other_mod_lists)

    def intersection_update(self, *other_mod_lists: Iterable[BaseMod]) -> None:
        next_mod_list: Iterable[BaseMod]
        next_mod_list, *other_mod_lists = other_mod_lists

        if isinstance(next_mod_list, ModList):
            self.__iand__(next_mod_list).intersection_update(*other_mod_lists)

        mod: BaseMod
        for mod in next_mod_list:
            mod_unique_identifier: str = mod.get_unique_identifier()
            if mod_unique_identifier not in self._mods:
                self._mods.pop(mod_unique_identifier)

        if other_mod_lists:
            self.intersection_update(*other_mod_lists)

    def isdisjoint(self, other_mod_list: Iterable[BaseMod]) -> bool:
        mod: BaseMod
        for mod in self:
            if mod in other_mod_list:
                return False

        return True

    def issubset(self, other_mod_list: Iterable[BaseMod]) -> bool:
        if isinstance(other_mod_list, ModList):
            return self.__le__(other_mod_list)

        mod: BaseMod
        for mod in self:
            if mod not in other_mod_list:
                return False

        return True

    def issuperset(self, other_mod_list: Iterable[BaseMod]) -> bool:
        if isinstance(other_mod_list, ModList):
            return self.__ge__(other_mod_list)

        mod: BaseMod
        for mod in other_mod_list:
            if mod not in self:
                return False

        return True

    def pop(self) -> BaseMod:
        return self._mods.popitem()[1]

    def remove(self, mod: BaseMod) -> None:
        self._mods.pop(mod.get_unique_identifier())

    def symmetric_difference(self, other_mod_list: Iterable[BaseMod]) -> Self:
        if isinstance(other_mod_list, ModList):
            return self.__xor__(other_mod_list)

        new_mod_list: ModList = ModList(())

        mod: BaseMod
        for mod in self:
            if mod not in other_mod_list:
                new_mod_list._mods[mod.get_unique_identifier()] = mod

        for mod in other_mod_list:
            mod_unique_identifier: str = mod.get_unique_identifier()
            if mod_unique_identifier not in self._mods:
                new_mod_list._mods[mod_unique_identifier] = mod

        return new_mod_list

    def symmetric_difference_update(self, other_mod_list: Iterable[BaseMod]) -> None:
        if isinstance(other_mod_list, ModList):
            self.__ixor__(other_mod_list)

        intersection: set[BaseMod] = set()

        mod: BaseMod
        for mod in self:
            if mod in other_mod_list:
                self._mods.pop(mod.get_unique_identifier())
                intersection.add(mod)

        for mod in other_mod_list:
            mod_unique_identifier: str = mod.get_unique_identifier()
            if mod_unique_identifier not in self._mods and mod not in intersection:
                self._mods[mod_unique_identifier] = mod

    def union(self, *other_mod_lists: Iterable[BaseMod]) -> Self:
        new_mod_list: ModList = ModList._from_mutable_mapping(self._mods)

        next_mod_list: Iterable[BaseMod]
        next_mod_list, *other_mod_lists = other_mod_lists
        if isinstance(next_mod_list, ModList):
            new_mod_list = new_mod_list.__or__(next_mod_list)

        else:
            for mod in next_mod_list:
                mod_unique_identifier: str = mod.get_unique_identifier()
                if mod_unique_identifier not in self._mods:
                    new_mod_list._mods[mod_unique_identifier] = mod

        return new_mod_list.union(*other_mod_lists)

    def update(self, *other_mod_lists: Iterable[BaseMod]) -> None:
        next_mod_list: Iterable[BaseMod]
        next_mod_list, *other_mod_lists = other_mod_lists

        if isinstance(next_mod_list, ModList):
            self.__ior__(next_mod_list).update(*other_mod_lists)

        for mod in next_mod_list:
            mod_unique_identifier: str = mod.get_unique_identifier()
            if mod_unique_identifier not in self._mods:
                self._mods[mod_unique_identifier] = mod

        if other_mod_lists:
            self.update(*other_mod_lists)

    def values(self) -> Iterable[BaseMod]:
        return self._mods.values()
