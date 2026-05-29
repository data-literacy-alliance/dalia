from django.db import models


class Page(models.Model):
    LANGUAGE_CHOICES = [
        ("de", "German"),
        ("en", "English"),
    ]

    slug = models.SlugField(max_length=100)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES)
    content_md = models.TextField(blank=True)
    docx_file = models.FileField(upload_to="pages/docx/", blank=True, null=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("slug", "language")]
        verbose_name = "Page"
        verbose_name_plural = "Pages"
        ordering = ["slug", "language"]

    def __str__(self):
        return f"{self.slug} ({self.get_language_display()})"
