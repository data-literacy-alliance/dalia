from __future__ import annotations

from curation.models.base import TimeStampedModel, UUIDMixin
from django.db import models
from django.utils import timezone

# Feature-specific constants
CONSENT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('granted', 'Granted'),
    ('withdrawn', 'Withdrawn'),
    ('expired', 'Expired'),
]

CONSENT_TYPES = [
    ('publication', 'Content Publication'),
    ('cc0_license', 'CC0 License Agreement'),
    ('data_processing', 'Data Processing'),
    ('analytics', 'Analytics Tracking'),
    ('marketing', 'Marketing Communications'),
]

GDPR_LAWFUL_BASIS = [
    ('consent', 'Article 6(1)(a) - Consent'),
    ('contract', 'Article 6(1)(b) - Contract'),
    ('legal_obligation', 'Article 6(1)(c) - Legal Obligation'),
    ('vital_interests', 'Article 6(1)(d) - Vital Interests'),
    ('public_task', 'Article 6(1)(e) - Public Task'),
    ('legitimate_interests', 'Article 6(1)(f) - Legitimate Interests'),
]


class ResourceConsent(UUIDMixin, TimeStampedModel):
    """
    Consent management for resource publication and usage.
    """
    resource_content = models.ForeignKey(
        "curation.ResourceContent",
        on_delete=models.CASCADE,
        related_name="consents"
    )
    person = models.ForeignKey(
        "curation.Person",
        on_delete=models.CASCADE,
        related_name="resource_consents"
    )
    consent_type = models.CharField(
        max_length=50,
        choices=CONSENT_TYPES,
        help_text="Type of consent being tracked"
    )
    status = models.CharField(
        max_length=20,
        choices=CONSENT_STATUS_CHOICES,
        default='pending'
    )

    # Consent lifecycle
    granted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this consent expires (if applicable)"
    )

    # Legal compliance
    legal_basis = models.CharField(
        max_length=50,
        choices=GDPR_LAWFUL_BASIS,
        default='consent',
        help_text="GDPR Article 6 lawful basis for processing"
    )
    consent_text = models.TextField(
        help_text="The exact text the person consented to"
    )
    consent_version = models.CharField(
        max_length=20,
        help_text="Version of consent terms"
    )

    # Technical details
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address when consent was given"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser/client information"
    )

    # Withdrawal details
    withdrawal_reason = models.TextField(
        blank=True,
        help_text="Reason given for withdrawal (optional)"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['resource_content', 'person', 'consent_type'],
                name='unique_resource_consent'
            )
        ]
        ordering = ('-created',)

    def __str__(self):
        return f"{self.person.full_name} - {self.get_consent_type_display()} - {self.get_status_display()}"

    def grant_consent(self, consent_text, version, ip_address=None, user_agent=None):
        """Grant consent with full audit trail."""
        self.status = 'granted'
        self.granted_at = timezone.now()
        self.consent_text = consent_text
        self.consent_version = version
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.save()

    def withdraw_consent(self, reason=None):
        """Withdraw consent with reason."""
        self.status = 'withdrawn'
        self.withdrawn_at = timezone.now()
        if reason:
            self.withdrawal_reason = reason
        self.save()

    def is_valid(self):
        """Check if consent is currently valid."""
        if self.status != 'granted':
            return False

        if self.expires_at and self.expires_at < timezone.now():
            self.status = 'expired'
            self.save()
            return False

        return True

    def can_withdraw(self):
        """Check if consent can be withdrawn."""
        return self.status == 'granted' and not self.is_permanent()

    def is_permanent(self):
        """Check if this is permanent consent that cannot be withdrawn."""
        # Some consent types might be permanent (e.g., publication under CC0)
        permanent_types = ['cc0_license']  # Add more as needed
        return self.consent_type in permanent_types and self.status == 'granted'


class ResourcePublishingConsent(UUIDMixin, TimeStampedModel):
    """
    Comprehensive consent for resource publishing with GDPR compliance.
    """
    resource_content = models.ForeignKey(
        "curation.ResourceContent",
        on_delete=models.CASCADE,
        related_name="publishing_consents"
    )
    consenting_person = models.ForeignKey(
        "curation.Person",
        on_delete=models.PROTECT,
        related_name="publishing_consents_given"
    )

    # Specific consent checkboxes
    cc0_agreed = models.BooleanField(
        default=False,
        help_text="Agreed to CC0 license terms"
    )
    data_processing_agreed = models.BooleanField(
        default=False,
        help_text="Consented to data processing"
    )
    public_display_agreed = models.BooleanField(
        default=False,
        help_text="Consented to public display of content"
    )
    analytics_agreed = models.BooleanField(
        default=False,
        help_text="Consented to analytics tracking"
    )

    # Terms of Service
    tos_version = models.CharField(
        max_length=20,
        help_text="Version of Terms of Service accepted"
    )
    privacy_policy_version = models.CharField(
        max_length=20,
        help_text="Version of Privacy Policy accepted"
    )

    # GDPR compliance
    gdpr_lawful_basis = models.CharField(
        max_length=50,
        choices=GDPR_LAWFUL_BASIS,
        default='consent'
    )
    data_retention_period = models.DurationField(
        null=True,
        blank=True,
        help_text="How long data will be retained"
    )

    # Withdrawal rights
    can_withdraw = models.BooleanField(
        default=True,
        help_text="Whether consent can be withdrawn"
    )
    withdrawal_instructions = models.TextField(
        default="Contact support to withdraw consent",
        help_text="Instructions for withdrawing consent"
    )

    # Audit trail
    consent_given_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Status tracking
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this consent is currently active"
    )
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawal_reason = models.TextField(blank=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f"Publishing consent for {self.resource_content.title} by {self.consenting_person.full_name}"

    def is_complete(self):
        """Check if all required consents are given."""
        required_fields = [
            self.cc0_agreed,
            self.data_processing_agreed,
            self.public_display_agreed,
        ]
        return all(required_fields)

    def withdraw_all(self, reason=None):
        """Withdraw all consents."""
        self.is_active = False
        self.withdrawn_at = timezone.now()
        if reason:
            self.withdrawal_reason = reason

        # Reset all consent flags
        self.cc0_agreed = False
        self.data_processing_agreed = False
        self.public_display_agreed = False
        self.analytics_agreed = False

        self.save()

    def get_consent_summary(self):
        """Get a summary of all consents given."""
        consents = []
        if self.cc0_agreed:
            consents.append("CC0 License")
        if self.data_processing_agreed:
            consents.append("Data Processing")
        if self.public_display_agreed:
            consents.append("Public Display")
        if self.analytics_agreed:
            consents.append("Analytics")
        return consents

    def data_subject_rights_info(self):
        """Return information about data subject rights under GDPR."""
        return {
            'lawful_basis': self.get_gdpr_lawful_basis_display(),
            'can_withdraw': self.can_withdraw,
            'withdrawal_instructions': self.withdrawal_instructions,
            'retention_period': self.data_retention_period,
            'rights': [
                'Right to access your data',
                'Right to rectification',
                'Right to erasure (if applicable)',
                'Right to restrict processing',
                'Right to data portability',
                'Right to object',
            ]
        }
