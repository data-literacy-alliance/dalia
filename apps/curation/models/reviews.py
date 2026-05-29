from __future__ import annotations

from curation.models.base import Activatable, TimeStampedModel, UUIDMixin
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Feature-specific constants
REVIEW_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('needs_revision', 'Needs Revision'),
]

QUESTION_TYPES = [
    ('text', 'Text'),
    ('choice', 'Multiple Choice'),
    ('rating', 'Rating'),
    ('boolean', 'Yes/No'),
    ('scale', 'Scale (1-10)'),
]


class Review(UUIDMixin, TimeStampedModel):
    """
    Flexible review system for resource content.
    """
    resource_content = models.ForeignKey(
        "curation.ResourceContent",
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_written"
    )
    status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='draft'
    )

    # Terms of Service and compliance tracking
    terms_version = models.CharField(
        max_length=20,
        help_text="Version of ToS accepted when creating this review"
    )

    # Review content
    summary = models.TextField(
        blank=True,
        help_text="Overall review summary"
    )
    recommendation = models.CharField(
        max_length=20,
        choices=[
            ('accept', 'Accept'),
            ('minor_revision', 'Accept with Minor Revisions'),
            ('major_revision', 'Major Revisions Required'),
            ('reject', 'Reject'),
        ],
        blank=True
    )

    # Timeline tracking
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Community context
    community = models.ForeignKey(
        "curation.Community",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Community context for this review"
    )

    class Meta:
        ordering = ('-created',)
        constraints = [
            models.UniqueConstraint(
                fields=['resource_content', 'reviewer'],
                name='unique_review_per_reviewer'
            )
        ]

    def __str__(self):
        return f"Review of {self.resource_content.title} by {self.reviewer.username}"

    def is_complete(self):
        """Check if review has all required answers."""
        required_questions = ReviewQuestion.objects.filter(
            community=self.community,
            required=True,
            is_active=True
        )
        answered_questions = self.answers.values_list('question_id', flat=True)
        return all(q.id in answered_questions for q in required_questions)

    def get_score(self):
        """Calculate average score from rating questions."""
        rating_answers = self.answers.filter(
            question__question_type__in=['rating', 'scale'],
            rating_answer__isnull=False
        )
        if not rating_answers.exists():
            return None

        total = sum(answer.rating_answer for answer in rating_answers)
        return total / rating_answers.count()


class ReviewQuestion(UUIDMixin, TimeStampedModel, Activatable):
    """
    Configurable review questions per community.
    """
    community = models.ForeignKey(
        "curation.Community",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Community-specific question (null = global)"
    )
    question_text = models.TextField(help_text="The question to ask reviewers")
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)

    # Configuration for choice/scale questions
    choices = models.JSONField(
        default=list,
        help_text="Available choices for choice-type questions (JSON array)"
    )
    min_value = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        help_text="Minimum value for rating/scale questions (default: 0)"
    )
    max_value = models.IntegerField(
        default=5,
        null=True,
        blank=True,
        help_text="Maximum value for rating/scale questions (default: 5)"
    )

    # Question metadata
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within review form"
    )
    required = models.BooleanField(
        default=True,
        help_text="Whether this question must be answered"
    )
    help_text_field = models.TextField(
        blank=True,
        db_column='help_text',
        help_text="Additional guidance for reviewers"
    )

    class Meta:
        ordering = ('community', 'order', 'question_text')

    def __str__(self):
        community_name = self.community.title if self.community else "Global"
        return f"{community_name}: {self.question_text[:50]}..."

    def clean(self):
        """Validate question configuration."""
        from django.core.exceptions import ValidationError

        if self.question_type in ['choice'] and not self.choices:
            raise ValidationError("Choice questions must have choices defined")

        if self.question_type in ['rating', 'scale']:
            if self.min_value is None or self.max_value is None:
                raise ValidationError("Rating/scale questions must have min and max values")
            if self.min_value >= self.max_value:
                raise ValidationError("Min value must be less than max value")


class ReviewAnswer(UUIDMixin, TimeStampedModel):
    """
    Answers to review questions with flexible data types.
    """
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(
        ReviewQuestion,
        on_delete=models.PROTECT,
        related_name="answers"
    )

    # Different answer types (only one should be filled)
    text_answer = models.TextField(blank=True)
    choice_answer = models.CharField(max_length=255, blank=True)
    rating_answer = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    boolean_answer = models.BooleanField(null=True, blank=True)

    # Additional context
    confidence = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Reviewer's confidence in their answer (1-5)"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['review', 'question'],
                name='unique_answer_per_question'
            )
        ]
        ordering = ('question__order',)

    def __str__(self):
        return f"Answer to '{self.question.question_text[:30]}...'"

    def get_answer_value(self):
        """Get the actual answer value regardless of type."""
        if self.text_answer:
            return self.text_answer
        elif self.choice_answer:
            return self.choice_answer
        elif self.rating_answer is not None:
            return self.rating_answer
        elif self.boolean_answer is not None:
            return self.boolean_answer
        return None

    def clean(self):
        """Validate that answer matches question type."""
        from django.core.exceptions import ValidationError

        answer_fields = [
            self.text_answer, self.choice_answer,
            self.rating_answer, self.boolean_answer
        ]
        filled_answers = [field for field in answer_fields if field is not None and field != '']

        if len(filled_answers) != 1:
            raise ValidationError("Exactly one answer field must be filled")

        # Validate answer type matches question type
        if self.question.question_type == 'text' and not self.text_answer:
            raise ValidationError("Text questions require text answers")
        elif self.question.question_type == 'choice' and not self.choice_answer:
            raise ValidationError("Choice questions require choice answers")
        elif self.question.question_type in ['rating', 'scale'] and self.rating_answer is None:
            raise ValidationError("Rating/scale questions require rating answers")
        elif self.question.question_type == 'boolean' and self.boolean_answer is None:
            raise ValidationError("Boolean questions require boolean answers")

        # Validate rating range
        if (self.rating_answer is not None and self.question.question_type in ['rating', 'scale']):
            if (self.rating_answer < self.question.min_value or
                    self.rating_answer > self.question.max_value):
                raise ValidationError(
                    f"Rating must be between {self.question.min_value} and {self.question.max_value}"
                )

        # Validate choice is in available choices
        if self.choice_answer and self.question.choices:
            if self.choice_answer not in self.question.choices:
                raise ValidationError(f"Choice must be one of: {', '.join(self.question.choices)}")
