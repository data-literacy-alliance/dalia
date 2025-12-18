import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "dalia.users"
    verbose_name = _("Users")

    def ready(self):
        with contextlib.suppress(ImportError):
            import dalia.users.signals  # noqa: F401, PLC0415
