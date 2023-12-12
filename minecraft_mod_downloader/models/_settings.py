"""
Django settings for inner "models" project & _mem_db_core app.
"""

from collections.abc import Sequence

__all__: Sequence[str] = ()

import inspect
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent


# Application definition

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "minecraft_mod_downloader.models._mem_db_core.app_config.MemDBCoreConfig"
]

MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]


# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "file::memory:?cache=shared",
    }
}


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = "en-gb"

TIME_ZONE = "Europe/London"

USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
