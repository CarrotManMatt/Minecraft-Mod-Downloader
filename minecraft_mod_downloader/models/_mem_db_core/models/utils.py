"""Utility classes & functions."""

from collections.abc import Sequence

__all__: Sequence[str] = ("BaseModel",)

from typing import Any, Final

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Model


class BaseModel(Model):
    """
    Base model, defining extra synchronous & asynchronous utility methods.

    This class is abstract so should not be instantiated or have a table made for it in the
    database (see https://docs.djangoproject.com/en/stable/topics/db/models/#abstract-base-classes).
    """

    class Meta:
        """Metadata options about this model."""

        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save the current instance to the database, only after the model has been cleaned.

        Cleaning the model ensures all data in the database is valid, even if the data was not
        added via a ModelForm (E.g. data is added using the ORM API).
        """
        self.full_clean()

        super().save(*args, **kwargs)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize a new model instance, capturing any proxy field values."""
        proxy_fields: dict[str, Any] = {
            field_name: kwargs.pop(field_name)
            for field_name
            in set(kwargs.keys()) & self.get_proxy_field_names()
        }

        super().__init__(*args, **kwargs)

        field_name: str
        value: Any
        for field_name, value in proxy_fields.items():
            setattr(self, field_name, value)

    def update(self, *, commit: bool = True, using: str | None = None, **kwargs: Any) -> None:
        """
        Change an in-memory object's values, then save it to the database.

        This simplifies the two steps into a single operation
        (based on Django's Queryset.bulk_update method).
        """
        unexpected_kwargs: set[str] = set()

        field_name: str
        for field_name in set(kwargs.keys()) - self.get_proxy_field_names():
            try:
                # noinspection PyUnresolvedReferences
                self._meta.get_field(field_name)
            except FieldDoesNotExist:
                unexpected_kwargs.add(field_name)

        if unexpected_kwargs:
            UNEXPECTED_KWARGS_MESSAGE: Final[str] = (
                f"{self._meta.model.__name__} got unexpected keyword arguments: "
                f"{tuple(unexpected_kwargs)}"
            )
            raise TypeError(UNEXPECTED_KWARGS_MESSAGE)

        value: Any
        for field_name, value in kwargs.items():
            setattr(self, field_name, value)

        if commit:
            self.save(using)

    update.alters_data: bool = True  # type: ignore[attr-defined, misc]

    @classmethod
    def get_proxy_field_names(cls) -> set[str]:
        """
        Return the set of extra names of properties that can be saved to the database.

        These are proxy fields because their values are not stored as object attributes,
        however, they can be used as a reference to a real attribute when saving objects to the
        database.
        """
        return set()
