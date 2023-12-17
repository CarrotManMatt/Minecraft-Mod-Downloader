from collections.abc import Sequence

__all__: Sequence[str] = ()

from collections.abc import Iterable

from django.db.models import Model
from django.db.models.signals import post_save
from django.dispatch import receiver


# noinspection PyUnusedLocal
@receiver(post_save, dispatch_uid="database_has_changed_signal_receiver")
def database_has_changed_signal_receiver(sender: type[Model], instance: Model, created: bool, raw: bool, using: str, update_fields: Iterable[str] | None, **kwargs: object) -> None:  # noqa: E501
    from minecraft_mod_downloader import config

    # noinspection PyProtectedMember
    if sender._meta.app_label == "_mem_db_core":
        config.set_database_has_changed(True, with_logging=False)
