from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "website"
    verbose_name = "Website (dalia.education)"

    def ready(self):
        from . import admin_groups

        admin_groups.install()
