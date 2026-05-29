from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import uuid


class EntityMapping(models.Model):
    """
    Mapping table between PostgreSQL entities (curation) and Fuseki entities.
    Provides bidirectional synchronization tracking and UUID4-based identity management.
    """

    # Entity Type Choices
    ENTITY_TYPE_CHOICES = [
        ('resource', 'Resource'),
        ('resource_content', 'Resource Content'),
        ('person', 'Person'),
        ('organization', 'Organization'),
        # ('discipline', 'Discipline'),  # Disabled: No transformer implemented
        ('license', 'License'),
        ('learning_resource_type', 'Learning Resource Type'),
        ('proficiency_level', 'Proficiency Level'),
        ('target_group', 'Target Group'),
        ('file_format', 'File Format'),
        ('media_type', 'Media Type'),
        ('language', 'Language'),
        ('community', 'Community'),
        ('relation_type', 'Relation Type'),
        ('relation_type_category', 'Relation Type Category'),
    ]

    # Synchronization Status Choices
    SYNC_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('synced', 'Synchronized'),
        ('failed', 'Failed'),
        ('outdated', 'Outdated'),
        ('conflict', 'Conflict'),
    ]

    # Sync Direction Choices
    DIRECTION_CHOICES = [
        ('postgresql_to_fuseki', 'PostgreSQL → Fuseki'),
        ('fuseki_to_postgresql', 'Fuseki → PostgreSQL'),
        ('bidirectional', 'Bidirectional'),
    ]

    # Primary identifiers
    postgresql_uuid = models.UUIDField(
        db_index=True,
        unique=True,
        null=True,
        blank=True,
        help_text="UUID4 of the entity in PostgreSQL (curation models)"
    )
    fuseki_uuid = models.UUIDField(
        db_index=True,
        unique=True,
        help_text="UUID4 of the entity in Fuseki graph database"
    )
    fuseki_uri = models.URLField(
        db_index=True,
        unique=True,
        validators=[URLValidator()],
        help_text="RDF URI of the entity in Fuseki"
    )

    # Entity classification
    entity_type = models.CharField(
        max_length=100,
        choices=ENTITY_TYPE_CHOICES,
        db_index=True,
        help_text="Type of entity being mapped"
    )

    # Synchronization tracking
    sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Current synchronization status"
    )
    sync_direction = models.CharField(
        max_length=30,
        choices=DIRECTION_CHOICES,
        default='bidirectional',
        help_text="Direction of synchronization"
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last successful synchronization"
    )

    # Import tracking for reverse sync (Fuseki → PostgreSQL)
    import_candidate = models.BooleanField(
        default=False,
        help_text="Entity exists in Fuseki but not in PostgreSQL"
    )
    import_approved = models.BooleanField(
        default=False,
        help_text="Import from Fuseki to PostgreSQL has been approved"
    )

    # Audit and metadata fields
    created = models.DateTimeField(default=timezone.now, editable=False)
    modified = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_entity_mappings',
        help_text="User who created this mapping"
    )
    sync_notes = models.TextField(
        blank=True,
        help_text="Notes about synchronization status, errors, or conflicts"
    )

    # Additional metadata from Fuseki
    fuseki_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata from Fuseki entity (labels, descriptions, etc.)"
    )

    class Meta:
        verbose_name = "Entity Mapping"
        verbose_name_plural = "Entity Mappings"
        ordering = ['-created']
        indexes = [
            models.Index(fields=['entity_type', 'sync_status']),
            models.Index(fields=['import_candidate', 'import_approved']),
            models.Index(fields=['created_by', 'created']),
        ]
        constraints = [
            # Ensure at least one UUID is present
            models.CheckConstraint(
                condition=~(
                    models.Q(postgresql_uuid__isnull=True) &
                    models.Q(fuseki_uuid__isnull=True)
                ),
                name='at_least_one_uuid_required'
            ),
            # Ensure import candidates have fuseki data but no postgresql data
            models.CheckConstraint(
                condition=~(
                    models.Q(import_candidate=True) &
                    models.Q(postgresql_uuid__isnull=False)
                ),
                name='import_candidates_no_postgresql_uuid'
            ),
            # Ensure synced entities have both UUIDs and they should match
            models.CheckConstraint(
                condition=~(
                    models.Q(sync_status='synced') &
                    models.Q(postgresql_uuid__isnull=False) &
                    models.Q(fuseki_uuid__isnull=False) &
                    ~models.Q(postgresql_uuid=models.F('fuseki_uuid'))
                ),
                name='synced_entities_matching_uuids'
            ),
        ]

    def clean(self):
        """Validate entity mapping data."""
        super().clean()

        # Ensure synced entities have matching UUIDs
        if (self.sync_status == 'synced' and
            self.postgresql_uuid and self.fuseki_uuid and
            self.postgresql_uuid != self.fuseki_uuid):
            raise ValidationError({
                'postgresql_uuid': 'PostgreSQL UUID must match Fuseki UUID for synced entities'
            })

        # Ensure import candidates don't have PostgreSQL UUID
        if self.import_candidate and self.postgresql_uuid:
            raise ValidationError({
                'postgresql_uuid': 'Import candidates should not have PostgreSQL UUID'
            })

    def mark_as_synced(self, postgresql_uuid=None):
        """Mark entity as synced with proper UUID synchronization."""
        if postgresql_uuid:
            self.postgresql_uuid = postgresql_uuid

        # For synced entities, ensure UUIDs match
        if self.postgresql_uuid and self.fuseki_uuid:
            if self.postgresql_uuid != self.fuseki_uuid:
                # Auto-sync UUIDs: use the existing PostgreSQL UUID if available
                self.fuseki_uuid = self.postgresql_uuid

        self.sync_status = 'synced'
        self.import_candidate = False
        self.import_approved = True
        self.last_sync_at = timezone.now()

    def __str__(self):
        status_display = f"[{self.get_sync_status_display()}]"
        if self.import_candidate:
            return f"{status_display} Import Candidate: {self.entity_type} - {self.fuseki_uri}"
        elif self.postgresql_uuid and self.fuseki_uuid:
            uuid_match = "✓" if self.postgresql_uuid == self.fuseki_uuid else "⚠"
            return f"{status_display} {self.entity_type}: PG:{self.postgresql_uuid} ↔ Fuseki:{self.fuseki_uuid} {uuid_match}"
        elif self.postgresql_uuid:
            return f"{status_display} {self.entity_type}: PG:{self.postgresql_uuid} → Fuseki:pending"
        else:
            return f"{status_display} {self.entity_type}: Fuseki:{self.fuseki_uuid}"

    def save(self, *args, **kwargs):
        """Override save to handle UUID generation and validation."""
        # Generate fuseki_uuid if not provided
        if not self.fuseki_uuid:
            self.fuseki_uuid = uuid.uuid4()

        # Update sync status based on mapping state
        if self.postgresql_uuid and self.fuseki_uuid and not self.import_candidate:
            if self.sync_status == 'pending':
                self.sync_status = 'synced'
                self.last_sync_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_bidirectional(self):
        """Check if entity exists in both systems."""
        return bool(self.postgresql_uuid and self.fuseki_uuid and not self.import_candidate)

    @property
    def needs_postgresql_creation(self):
        """Check if PostgreSQL entity needs to be created from Fuseki data."""
        return self.import_candidate and not self.postgresql_uuid

    @property
    def sync_age_days(self):
        """Calculate days since last sync."""
        if not self.last_sync_at:
            return None
        return (timezone.now() - self.last_sync_at).days

    @classmethod
    def get_import_candidates(cls, entity_type=None):
        """Get entities that exist in Fuseki but not in PostgreSQL."""
        queryset = cls.objects.filter(import_candidate=True, postgresql_uuid__isnull=True)
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        return queryset

    @classmethod
    def get_unsynced_entities(cls, entity_type=None):
        """Get entities that need synchronization."""
        queryset = cls.objects.filter(sync_status__in=['pending', 'failed', 'outdated'])
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        return queryset

    @classmethod
    def get_by_postgresql_uuid(cls, uuid_value):
        """Get mapping by PostgreSQL UUID."""
        try:
            return cls.objects.get(postgresql_uuid=uuid_value)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_fuseki_uuid(cls, uuid_value):
        """Get mapping by Fuseki UUID."""
        try:
            return cls.objects.get(fuseki_uuid=uuid_value)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_fuseki_uri(cls, uri):
        """Get mapping by Fuseki URI."""
        try:
            return cls.objects.get(fuseki_uri=uri)
        except cls.DoesNotExist:
            return None


class SyncLog(models.Model):
    """
    Audit log for synchronization operations.
    """

    ACTION_CHOICES = [
        ('create_mapping', 'Create Mapping'),
        ('update_mapping', 'Update Mapping'),
        ('sync_to_fuseki', 'Sync to Fuseki'),
        ('import_from_fuseki', 'Import from Fuseki'),
        ('bulk_operation', 'Bulk Operation'),
        ('conflict_resolution', 'Conflict Resolution'),
    ]

    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('warning', 'Warning'),
    ]

    entity_mapping = models.ForeignKey(
        EntityMapping,
        on_delete=models.CASCADE,
        related_name='sync_logs',
        null=True,
        blank=True,
        help_text="Related entity mapping (if applicable)"
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)

    created = models.DateTimeField(default=timezone.now, editable=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='sync_logs'
    )

    class Meta:
        verbose_name = "Sync Log"
        verbose_name_plural = "Sync Logs"
        ordering = ['-created']
        indexes = [
            models.Index(fields=['action', 'status']),
            models.Index(fields=['created_by', 'created']),
        ]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.get_action_display()} at {self.created}"