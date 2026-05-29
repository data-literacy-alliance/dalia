"""
Admin classes for profile models (Person, Organization).
"""
from core.admin import BaseModelAdmin
from curation.models import Organization, Person
from django.contrib import admin


@admin.register(Person)
class PersonAdmin(BaseModelAdmin):
    list_display = ("first_name", "last_name", "orcid", "homepage", "is_active", "uuid")
    search_fields = ("first_name", "last_name", "orcid", "user__username", "uuid")
    list_filter = ("is_active", "privacy_level", "email_notifications")
    readonly_fields = ("uuid",)


@admin.register(Organization)
class OrganizationAdmin(BaseModelAdmin):
    list_display = ("name", "ror_id", "homepage", "is_active", "uuid")
    search_fields = ("name", "ror_id", "uuid")
    list_filter = ("is_active",)
    readonly_fields = ("uuid",)
