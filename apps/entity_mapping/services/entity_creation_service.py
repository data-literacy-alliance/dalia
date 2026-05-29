"""
Entity Creation Service for Entity Mapping System

Creates PostgreSQL entities from approved import candidates.
Provides transaction support, duplicate detection, and comprehensive error handling.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from django.db import transaction
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.apps import apps

from ..models import EntityMapping, SyncLog
from .transformation_service import TransformationService, ValidationResult


@dataclass
class EntityCreationResult:
    """Result of entity creation operation"""
    success: bool
    entity_mapping_id: Optional[int]
    postgresql_uuid: Optional[str]
    entity_pk: Optional[int]
    message: str
    errors: List[str]
    warnings: List[str]
    entity_obj: Any = None  # The created entity object

    def __str__(self):
        if self.success:
            return f"✅ {self.message}"
        else:
            return f"❌ {self.message}"


class EntityCreationService:
    """
    Service for creating PostgreSQL entities from approved import candidates.
    Handles transformation, validation, duplicate detection, and database operations.
    """

    # Mapping of entity types to Django model strings (lazy loading)
    MODEL_MAPPING = {
        'license': 'curation.License',
        'learning_resource_type': 'curation.LearningResourceType',
        'proficiency_level': 'curation.ProficiencyLevel',
        'target_group': 'curation.TargetGroup',
        'file_format': 'curation.FileFormat',
        'media_type': 'curation.MediaType',
        'language': 'curation.Language',
        'community': 'curation.Community',
    }

    @staticmethod
    def _get_model_class(entity_type: str):
        """
        Get Django model class for entity type using lazy loading.

        Args:
            entity_type: Type of entity

        Returns:
            Django model class or None if not found
        """
        model_string = EntityCreationService.MODEL_MAPPING.get(entity_type)
        if not model_string:
            return None

        # Use Django's apps registry for safe lazy loading
        app_label, model_name = model_string.split('.')
        return apps.get_model(app_label, model_name)

    def __init__(self, user: User):
        """
        Initialize service with user context

        Args:
            user: User performing the operation (for audit logging)
        """
        self.user = user

    def create_entity_from_mapping(
        self,
        entity_mapping: EntityMapping,
        force: bool = False
    ) -> EntityCreationResult:
        """
        Create PostgreSQL entity from an EntityMapping import candidate

        Args:
            entity_mapping: EntityMapping instance (must be approved import candidate)
            force: If True, skip some safety checks (use with caution)

        Returns:
            EntityCreationResult with success status and details
        """
        # Validation: Check that this is an approved import candidate
        if not entity_mapping.import_approved and not force:
            return EntityCreationResult(
                success=False,
                entity_mapping_id=entity_mapping.id,
                postgresql_uuid=None,
                entity_pk=None,
                message="Entity mapping is not approved for import",
                errors=["Import not approved - approve first or use force=True"],
                warnings=[]
            )

        # Validation: Check that PostgreSQL entity doesn't already exist
        if entity_mapping.postgresql_uuid and not force:
            return EntityCreationResult(
                success=False,
                entity_mapping_id=entity_mapping.id,
                postgresql_uuid=str(entity_mapping.postgresql_uuid),
                entity_pk=None,
                message="PostgreSQL entity already exists",
                errors=["Entity already created - postgresql_uuid is set"],
                warnings=[]
            )

        # Check if model is supported
        model_class = self._get_model_class(entity_mapping.entity_type)
        if not model_class:
            return EntityCreationResult(
                success=False,
                entity_mapping_id=entity_mapping.id,
                postgresql_uuid=None,
                entity_pk=None,
                message=f"Unsupported entity type: {entity_mapping.entity_type}",
                errors=[f"No model mapping for entity type '{entity_mapping.entity_type}'"],
                warnings=[]
            )

        # Step 1: Transform Fuseki metadata to Django model data
        transformation_result = TransformationService.transform_entity(
            entity_mapping.entity_type,
            entity_mapping.fuseki_metadata
        )

        if not transformation_result.is_valid:
            return EntityCreationResult(
                success=False,
                entity_mapping_id=entity_mapping.id,
                postgresql_uuid=None,
                entity_pk=None,
                message="Transformation validation failed",
                errors=transformation_result.errors,
                warnings=transformation_result.warnings
            )

        # Step 2: Check for duplicate entities in PostgreSQL
        duplicate_check = self._check_duplicates(
            model_class,
            transformation_result.cleaned_data,
            entity_mapping.entity_type
        )

        if duplicate_check['exists'] and not force:
            return EntityCreationResult(
                success=False,
                entity_mapping_id=entity_mapping.id,
                postgresql_uuid=None,
                entity_pk=None,
                message=f"Duplicate entity found: {duplicate_check['message']}",
                errors=[duplicate_check['message']],
                warnings=transformation_result.warnings
            )

        # Step 3: Create PostgreSQL entity with transaction
        try:
            with transaction.atomic():
                # Create the entity
                entity_obj = self._create_entity(
                    model_class,
                    transformation_result.cleaned_data,
                    entity_mapping
                )

                # Update EntityMapping with postgresql_uuid
                entity_mapping.postgresql_uuid = entity_obj.uuid
                entity_mapping.sync_status = 'synced'
                entity_mapping.last_sync_at = timezone.now()
                entity_mapping.import_candidate = False
                entity_mapping.save()

                # Log success
                SyncLog.objects.create(
                    entity_mapping=entity_mapping,
                    action='import_from_fuseki',
                    status='success',
                    message=f"Successfully created {entity_mapping.entity_type} entity",
                    details={
                        'postgresql_uuid': str(entity_obj.uuid),
                        'entity_pk': entity_obj.pk,
                        'cleaned_data': transformation_result.cleaned_data,
                        'warnings': transformation_result.warnings
                    },
                    created_by=self.user
                )

                return EntityCreationResult(
                    success=True,
                    entity_mapping_id=entity_mapping.id,
                    postgresql_uuid=str(entity_obj.uuid),
                    entity_pk=entity_obj.pk,
                    message=f"Successfully created {entity_mapping.entity_type}: {entity_obj}",
                    errors=[],
                    warnings=transformation_result.warnings,
                    entity_obj=entity_obj
                )

        except Exception as e:
            # Log failure
            SyncLog.objects.create(
                entity_mapping=entity_mapping,
                action='import_from_fuseki',
                status='error',
                message=f"Failed to create {entity_mapping.entity_type} entity",
                details={
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'cleaned_data': transformation_result.cleaned_data
                },
                created_by=self.user
            )

            return EntityCreationResult(
                success=False,
                entity_mapping_id=entity_mapping.id,
                postgresql_uuid=None,
                entity_pk=None,
                message=f"Database error: {str(e)}",
                errors=[str(e)],
                warnings=transformation_result.warnings
            )

    def _create_entity(
        self,
        model_class: Any,
        cleaned_data: Dict[str, Any],
        entity_mapping: EntityMapping
    ) -> Any:
        """
        Create entity instance in database with UUID synchronization.

        IMPORTANT: When importing from Fuseki, we use the fuseki_uuid as the
        PostgreSQL entity UUID to maintain consistency and satisfy the
        synced_entities_matching_uuids constraint.

        Args:
            model_class: Django model class
            cleaned_data: Validated and cleaned data
            entity_mapping: Source EntityMapping

        Returns:
            Created entity instance with synced UUID
        """
        # Special handling for Community (uses 'title' instead of 'label')
        Community = apps.get_model('curation', 'Community')
        if model_class == Community:
            # Community uses 'title' field instead of 'label'
            if 'label' in cleaned_data and 'title' not in cleaned_data:
                cleaned_data['title'] = cleaned_data.pop('label')

            # Use fuseki_uuid for the PostgreSQL entity to ensure UUIDs match
            cleaned_data['uuid'] = entity_mapping.fuseki_uuid
            entity_obj = model_class.objects.create(**cleaned_data)
        else:
            # Standard vocabulary models
            # Use fuseki_uuid for the PostgreSQL entity to ensure UUIDs match
            cleaned_data['uuid'] = entity_mapping.fuseki_uuid
            entity_obj = model_class.objects.create(**cleaned_data)

        return entity_obj

    def _check_duplicates(
        self,
        model_class: Any,
        cleaned_data: Dict[str, Any],
        entity_type: str
    ) -> Dict[str, Any]:
        """
        Check for duplicate entities in PostgreSQL

        Args:
            model_class: Django model class
            cleaned_data: Validated and cleaned data
            entity_type: Type of entity

        Returns:
            Dict with 'exists' (bool) and 'message' (str)
        """
        # Check by label/title
        lookup_field = 'title' if entity_type == 'community' else 'label'
        lookup_value = cleaned_data.get(lookup_field)

        if lookup_value:
            existing = model_class.objects.filter(**{lookup_field: lookup_value}).first()
            if existing:
                return {
                    'exists': True,
                    'message': f"{entity_type} with {lookup_field} '{lookup_value}' already exists (UUID: {existing.uuid})"
                }

        # Check by slug
        slug = cleaned_data.get('slug')
        if slug:
            existing = model_class.objects.filter(slug=slug).first()
            if existing:
                return {
                    'exists': True,
                    'message': f"{entity_type} with slug '{slug}' already exists (UUID: {existing.uuid})"
                }

        # Check by URI
        uri = cleaned_data.get('uri')
        if uri:
            existing = model_class.objects.filter(uri=uri).first()
            if existing:
                return {
                    'exists': True,
                    'message': f"{entity_type} with URI '{uri}' already exists (UUID: {existing.uuid})"
                }

        # License-specific: check by SPDX ID
        if entity_type == 'license' and 'spdx_id' in cleaned_data:
            spdx_id = cleaned_data.get('spdx_id')
            if spdx_id:
                License = apps.get_model('curation', 'License')
                existing = License.objects.filter(spdx_id=spdx_id).first()
                if existing:
                    return {
                        'exists': True,
                        'message': f"License with SPDX ID '{spdx_id}' already exists (UUID: {existing.uuid})"
                    }

        return {'exists': False, 'message': ''}

    def validate_before_creation(
        self,
        entity_mapping: EntityMapping
    ) -> ValidationResult:
        """
        Validate entity mapping before attempting creation (dry-run)

        Args:
            entity_mapping: EntityMapping to validate

        Returns:
            ValidationResult with validation status
        """
        return TransformationService.transform_entity(
            entity_mapping.entity_type,
            entity_mapping.fuseki_metadata
        )

    def bulk_create_entities(
        self,
        entity_mappings: List[EntityMapping],
        stop_on_error: bool = False
    ) -> Tuple[List[EntityCreationResult], Dict[str, int]]:
        """
        Create multiple entities in bulk

        Args:
            entity_mappings: List of EntityMapping instances
            stop_on_error: If True, stop processing on first error

        Returns:
            Tuple of (results list, statistics dict)
        """
        results = []
        stats = {
            'total': len(entity_mappings),
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        for entity_mapping in entity_mappings:
            result = self.create_entity_from_mapping(entity_mapping)
            results.append(result)

            if result.success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
                if stop_on_error:
                    # Mark remaining as skipped
                    remaining = len(entity_mappings) - len(results)
                    stats['skipped'] = remaining
                    break

        return results, stats

    def preview_transformation(
        self,
        entity_mapping: EntityMapping
    ) -> Dict[str, Any]:
        """
        Preview what the created entity would look like (without creating it)

        Args:
            entity_mapping: EntityMapping to preview

        Returns:
            Dict with preview data
        """
        validation_result = self.validate_before_creation(entity_mapping)

        model_class = self._get_model_class(entity_mapping.entity_type)
        model_name = model_class.__name__ if model_class else "Unknown"

        # Check for duplicates
        duplicate_check = {'exists': False, 'message': ''}
        if validation_result.is_valid and model_class:
            duplicate_check = self._check_duplicates(
                model_class,
                validation_result.cleaned_data,
                entity_mapping.entity_type
            )

        return {
            'entity_mapping_id': entity_mapping.id,
            'entity_type': entity_mapping.entity_type,
            'model_name': model_name,
            'fuseki_uri': entity_mapping.fuseki_uri,
            'fuseki_uuid': str(entity_mapping.fuseki_uuid),
            'is_valid': validation_result.is_valid,
            'errors': validation_result.errors,
            'warnings': validation_result.warnings,
            'cleaned_data': validation_result.cleaned_data,
            'has_duplicates': duplicate_check['exists'],
            'duplicate_message': duplicate_check.get('message', ''),
            'can_create': validation_result.is_valid and not duplicate_check['exists'],
            'import_approved': entity_mapping.import_approved
        }

    @classmethod
    def get_supported_entity_types(cls) -> List[str]:
        """Get list of supported entity types"""
        return list(cls.MODEL_MAPPING.keys())

    @classmethod
    def is_entity_type_supported(cls, entity_type: str) -> bool:
        """Check if entity type is supported"""
        return entity_type in cls.MODEL_MAPPING