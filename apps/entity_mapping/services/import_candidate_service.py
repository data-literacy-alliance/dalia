"""
Import candidate detection service.
This service identifies entities that exist in Fuseki but are missing from PostgreSQL,
creating import candidate mappings for admin review and approval.
"""

import logging
import uuid
from typing import Dict, List, Optional, Set, Tuple
from django.db import transaction
from django.contrib.auth import get_user_model
User = get_user_model()

from curation.models import (
    License, LearningResourceType, ProficiencyLevel,
    TargetGroup, MediaType, Language, Community, Person, Organization
    # Discipline excluded: No transformer implemented
)
from entity_mapping.models import EntityMapping, SyncLog
from entity_mapping.services.fuseki_query_service import FusekiQueryService


logger = logging.getLogger(__name__)


class ImportCandidateService:
    """
    Service for detecting and managing import candidates.
    Identifies entities that exist in Fuseki but not in PostgreSQL.
    """

    # Mapping of entity types to their corresponding Django models
    ENTITY_MODEL_MAPPING = {
        'license': License,
        # 'discipline': Discipline,  # Disabled: No transformer implemented
        'learning_resource_type': LearningResourceType,
        'proficiency_level': ProficiencyLevel,
        'target_group': TargetGroup,
        'media_type': MediaType,
        'language': Language,
        'community': Community,
        # Note: person and organization are not supported by current Fuseki service
        # 'person': Person,
        # 'organization': Organization,
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.fuseki_service = FusekiQueryService()

    def discover_import_candidates(
        self,
        entity_type: Optional[str] = None,
        user: Optional[User] = None,
        limit: int = 1000
    ) -> Dict[str, int]:
        """
        Discover entities that exist in Fuseki but not in PostgreSQL.

        Args:
            entity_type: Specific entity type to check, or None for all types
            user: User to assign as creator of import candidate mappings
            limit: Maximum number of entities to check per type

        Returns:
            Dictionary with entity types as keys and counts of new candidates found
        """
        if not user:
            # Get or create a system user for automated operations
            user, created = User.objects.get_or_create(
                username='system_import_service',
                defaults={
                    'email': 'system@dalia.education',
                    'first_name': 'Import',
                    'last_name': 'Service',
                    'is_active': False,  # System user, not for login
                }
            )

        entity_types = [entity_type] if entity_type else list(self.ENTITY_MODEL_MAPPING.keys())
        results = {}

        for etype in entity_types:
            try:
                count = self._discover_candidates_for_type(etype, user, limit)
                results[etype] = count
                self.logger.info(f"Found {count} new import candidates for {etype}")
            except Exception as e:
                self.logger.error(f"Error discovering candidates for {etype}: {e}")
                results[etype] = 0

        return results

    def _discover_candidates_for_type(self, entity_type: str, user: User, limit: int) -> int:
        """
        Discover import candidates for a specific entity type.

        Args:
            entity_type: Type of entity to check
            user: User to assign as creator
            limit: Maximum entities to check

        Returns:
            Number of new candidates found
        """
        if entity_type not in self.ENTITY_MODEL_MAPPING:
            self.logger.warning(f"Unknown entity type: {entity_type}")
            return 0

        # Get entities from Fuseki
        fuseki_entities = self.fuseki_service.discover_all_entities_by_type(entity_type, limit)
        if not fuseki_entities:
            return 0

        # Get existing mappings and PostgreSQL entities
        existing_fuseki_uris = set(
            EntityMapping.objects.filter(entity_type=entity_type)
            .values_list('fuseki_uri', flat=True)
        )

        model_class = self.ENTITY_MODEL_MAPPING[entity_type]
        existing_postgresql_uris = set()

        # For entities that might have URI fields, check those too
        if hasattr(model_class, 'uri'):
            existing_postgresql_uris.update(
                model_class.objects.exclude(uri='')
                .values_list('uri', flat=True)
            )

        new_candidates = 0

        with transaction.atomic():
            for entity_data in fuseki_entities:
                fuseki_uri = entity_data['fuseki_uri']

                # Skip if we already have a mapping for this URI
                if fuseki_uri in existing_fuseki_uris:
                    continue

                # Skip if this URI exists in PostgreSQL
                if fuseki_uri in existing_postgresql_uris:
                    continue

                # Check if we can find a matching PostgreSQL entity by other criteria
                if self._find_matching_postgresql_entity(entity_data, model_class):
                    continue

                # Create import candidate mapping
                try:
                    mapping = EntityMapping.objects.create(
                        fuseki_uuid=entity_data['fuseki_uuid'] or str(uuid.uuid4()),
                        fuseki_uri=fuseki_uri,
                        entity_type=entity_type,
                        import_candidate=True,
                        import_approved=False,
                        sync_status='pending',
                        sync_direction='fuseki_to_postgresql',
                        created_by=user,
                        fuseki_metadata=entity_data['metadata'],
                        sync_notes=f"Auto-discovered import candidate from Fuseki"
                    )

                    # Log the discovery
                    SyncLog.objects.create(
                        entity_mapping=mapping,
                        action='create_mapping',
                        status='success',
                        message=f"Import candidate discovered for {entity_type}",
                        details={
                            'fuseki_uri': fuseki_uri,
                            'metadata': entity_data['metadata']
                        },
                        created_by=user
                    )

                    new_candidates += 1

                except Exception as e:
                    self.logger.error(f"Error creating import candidate for {fuseki_uri}: {e}")
                    continue

        return new_candidates

    def _find_matching_postgresql_entity(self, entity_data: Dict, model_class) -> Optional[object]:
        """
        Try to find a matching PostgreSQL entity using various criteria.

        Args:
            entity_data: Entity data from Fuseki
            model_class: Django model class to search

        Returns:
            Matching model instance or None
        """
        metadata = entity_data['metadata']
        label = metadata.get('label', '').strip()

        if not label:
            return None

        try:
            # Try exact label match
            if hasattr(model_class, 'label'):
                match = model_class.objects.filter(label__iexact=label).first()
                if match:
                    return match

            # Try exact name match
            if hasattr(model_class, 'name'):
                match = model_class.objects.filter(name__iexact=label).first()
                if match:
                    return match

            # For licenses, try SPDX ID match
            if hasattr(model_class, 'spdx_id') and metadata.get('license_id'):
                match = model_class.objects.filter(
                    spdx_id__iexact=metadata['license_id']
                ).first()
                if match:
                    return match

            # For languages, try code match (extracted from URI)
            if hasattr(model_class, 'code') and metadata.get('code'):
                match = model_class.objects.filter(
                    code__iexact=metadata['code']
                ).first()
                if match:
                    return match

            # For persons, try name components
            if hasattr(model_class, 'first_name') and hasattr(model_class, 'last_name'):
                first_name = metadata.get('first_name', '').strip()
                last_name = metadata.get('last_name', '').strip()
                if first_name and last_name:
                    match = model_class.objects.filter(
                        first_name__iexact=first_name,
                        last_name__iexact=last_name
                    ).first()
                    if match:
                        return match

        except Exception as e:
            self.logger.debug(f"Error searching for matching entity: {e}")

        return None

    def get_import_candidates_summary(self) -> Dict[str, Dict[str, int]]:
        """
        Get a summary of import candidates by entity type and approval status.

        Returns:
            Dictionary with entity types and their candidate counts
        """
        summary = {}

        for entity_type in self.ENTITY_MODEL_MAPPING.keys():
            candidates = EntityMapping.objects.filter(
                entity_type=entity_type,
                import_candidate=True
            )

            summary[entity_type] = {
                'total': candidates.count(),
                'pending': candidates.filter(import_approved=False).count(),
                'approved': candidates.filter(import_approved=True).count(),
            }

        return summary

    def approve_import_candidate(self, mapping_id: int, user: User) -> bool:
        """
        Approve an import candidate for PostgreSQL creation.

        Args:
            mapping_id: ID of the EntityMapping to approve
            user: User approving the import

        Returns:
            True if successful, False otherwise
        """
        try:
            with transaction.atomic():
                mapping = EntityMapping.objects.select_for_update().get(
                    id=mapping_id,
                    import_candidate=True,
                    import_approved=False
                )

                mapping.import_approved = True
                mapping.sync_notes += f"\nApproved by {user.username} for import"
                mapping.save()

                # Log the approval
                SyncLog.objects.create(
                    entity_mapping=mapping,
                    action='import_from_fuseki',
                    status='success',
                    message=f"Import candidate approved for {mapping.entity_type}",
                    details={'approved_by': user.username},
                    created_by=user
                )

                self.logger.info(f"Import candidate {mapping_id} approved by {user.username}")
                return True

        except EntityMapping.DoesNotExist:
            self.logger.warning(f"Import candidate {mapping_id} not found or already processed")
            return False
        except Exception as e:
            self.logger.error(f"Error approving import candidate {mapping_id}: {e}")
            return False

    def reject_import_candidate(self, mapping_id: int, user: User, reason: str = "") -> bool:
        """
        Reject an import candidate.

        Args:
            mapping_id: ID of the EntityMapping to reject
            user: User rejecting the import
            reason: Optional reason for rejection

        Returns:
            True if successful, False otherwise
        """
        try:
            with transaction.atomic():
                mapping = EntityMapping.objects.select_for_update().get(
                    id=mapping_id,
                    import_candidate=True
                )

                mapping.sync_status = 'failed'
                mapping.sync_notes += f"\nRejected by {user.username}: {reason}"
                mapping.save()

                # Log the rejection
                SyncLog.objects.create(
                    entity_mapping=mapping,
                    action='import_from_fuseki',
                    status='error',
                    message=f"Import candidate rejected for {mapping.entity_type}",
                    details={
                        'rejected_by': user.username,
                        'reason': reason
                    },
                    created_by=user
                )

                self.logger.info(f"Import candidate {mapping_id} rejected by {user.username}")
                return True

        except EntityMapping.DoesNotExist:
            self.logger.warning(f"Import candidate {mapping_id} not found")
            return False
        except Exception as e:
            self.logger.error(f"Error rejecting import candidate {mapping_id}: {e}")
            return False

    def cleanup_old_candidates(self, days_old: int = 30) -> int:
        """
        Clean up old rejected or processed import candidates.

        Args:
            days_old: Remove candidates older than this many days

        Returns:
            Number of candidates removed
        """
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days_old)

        # Remove old rejected candidates
        old_candidates = EntityMapping.objects.filter(
            import_candidate=True,
            sync_status='failed',
            created__lt=cutoff_date
        )

        count = old_candidates.count()
        old_candidates.delete()

        self.logger.info(f"Cleaned up {count} old import candidates")
        return count