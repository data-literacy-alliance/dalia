from __future__ import annotations

from curation.models.base import NamedVocabulary
from django.db import models


class LearningResourceType(NamedVocabulary):
    """
    Types of learning resources (course, tutorial, dataset, etc.)
    """
    pass


class Discipline(NamedVocabulary):
    """
    Research domains and disciplines with hierarchical structure
    """
    parent_id = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent discipline for hierarchical organization"
    )
    parent_label = models.CharField(
        max_length=255,
        blank=True,
        help_text="Label of the parent discipline for display purposes"
    )

    class Meta(NamedVocabulary.Meta):
        verbose_name = "Discipline"
        verbose_name_plural = "Disciplines"

    def save(self, *args, **kwargs):
        # Auto-populate parent_label from parent_id
        if self.parent_id and not self.parent_label:
            self.parent_label = self.parent_id.label
        elif not self.parent_id:
            self.parent_label = ""
        super().save(*args, **kwargs)

    @classmethod
    def get_root_disciplines(cls):
        """Get all top-level disciplines (where parent_id is NULL)"""
        return cls.objects.filter(parent_id__isnull=True, is_active=True)

    @classmethod
    def get_children_of(cls, parent_id):
        """Get all child disciplines of a specific parent"""
        return cls.objects.filter(parent_id=parent_id, is_active=True)

    def get_children(self):
        """Get direct children of this discipline"""
        return self.__class__.objects.filter(parent_id=self.pk, is_active=True)

    def get_descendants(self):
        """Get all descendants (recursive children) of this discipline"""
        descendants = []
        children = self.get_children()
        for child in children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def get_ancestors(self):
        """Get all ancestors (recursive parents) of this discipline"""
        ancestors = []
        if self.parent_id:
            ancestors.append(self.parent_id)
            ancestors.extend(self.parent_id.get_ancestors())
        return ancestors

    def get_level(self):
        """Get the depth level of this discipline in the hierarchy"""
        return len(self.get_ancestors())

    def is_root(self):
        """Check if this is a root-level discipline"""
        return self.parent_id is None


class License(NamedVocabulary):
    """
    Licensing information with SPDX integration
    """
    spdx_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="Optional SPDX identifier (e.g., MIT, GPL-3.0, CC-BY-4.0)"
    )


class ProficiencyLevel(NamedVocabulary):
    """
    Skill levels required (beginner, intermediate, advanced)
    """
    pass


class TargetGroup(NamedVocabulary):
    """
    Target audiences (researchers, students, practitioners)
    """
    pass


class FileFormat(NamedVocabulary):
    """
    File formats supported (PDF, CSV, JSON, etc.)
    """
    pass


class MediaType(NamedVocabulary):
    """
    Media types (text, video, interactive, etc.)
    """
    pass


class Language(NamedVocabulary):
    """
    Language codes with ISO 639-1 support for multilingual content.
    """
    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="ISO 639-1 language code (e.g., 'en', 'de', 'fr')"
    )
    native_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Native language name (e.g., 'English', 'Deutsch', 'Francais')"
    )

    class Meta(NamedVocabulary.Meta):
        verbose_name = "Language"
        verbose_name_plural = "Languages"
        ordering = ("code",)

    def __str__(self):
        if self.native_name:
            return f"{self.label} ({self.code}) - {self.native_name}"
        return f"{self.label} ({self.code})"
