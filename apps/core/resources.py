"""
Core import/export resources.
Base resource classes for django-import-export.
"""

from import_export import resources
from import_export.fields import Field


class ImportExportResource(resources.ModelResource):
    """
    Base resource class for all ICZ models.
    Provides common configuration for django-import-export.

    Usage:
        class MyModelResource(ImportExportResource):
            class Meta:
                model = MyModel
                fields = ('id', 'name', 'code', 'created_at')
                export_order = ('id', 'code', 'name', 'created_at')
    """

    # Add created_at and updated_at as read-only fields by default
    created_at = Field(attribute="created_at", readonly=True)
    updated_at = Field(attribute="updated_at", readonly=True)

    class Meta:
        # Common configuration
        skip_unchanged = True
        report_skipped = True
        clean_model_instances = True
        # Exclude these fields from import by default (can override in subclasses)
        exclude = ("id",)

    def before_import_row(self, row, **kwargs):
        """
        Hook to preprocess each row before import.
        Override in subclasses to add custom validation or transformation.
        """
        return super().before_import_row(row, **kwargs)

    def after_import_row(self, row, row_result, **kwargs):
        """
        Hook to post-process each row after import.
        Override in subclasses to add custom logging or side effects.
        """
        return super().after_import_row(row, row_result, **kwargs)
