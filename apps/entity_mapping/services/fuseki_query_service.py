"""
Fuseki entity discovery service using existing DALIA suggest functions.
This service leverages the existing dalia.curation.suggest modules to discover entities
that exist in Fuseki but may not be present in the PostgreSQL curation models.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any

from search.suggest import (
    licenses, learning_resource_types, proficiency_levels,
    target_groups, media_types, languages, communities
    # disciplines excluded: No transformer implemented
)
from search.api_models.api_models import (
    CurationSuggestSearchRequest, CurationSuggestLicensesRequest
)


logger = logging.getLogger(__name__)


class FusekiQueryService:
    """
    Service for discovering entities from Fuseki using existing DALIA suggest functions.
    Uses dalia.curation.suggest modules to find entities that exist in Fuseki.
    """

    # Supported entity types
    SUPPORTED_ENTITY_TYPES = {
        'license',
        # 'discipline',  # Disabled: No transformer implemented
        'learning_resource_type',
        'proficiency_level',
        'target_group',
        'media_type',
        'language',
        'community'
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def discover_all_entities_by_type(self, entity_type: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Discover all entities of a specific type using DALIA suggest functions.

        Args:
            entity_type: Type of entity to discover (e.g., 'license', 'discipline')
            limit: Maximum number of entities to return

        Returns:
            List of dictionaries containing entity metadata
        """
        if entity_type not in self.SUPPORTED_ENTITY_TYPES:
            self.logger.warning(f"Unknown entity type: {entity_type}")
            return []

        try:
            # Call the appropriate suggest function based on entity type
            if entity_type == 'license':
                request = CurationSuggestLicensesRequest(q='*', limit=limit, offset=0, filter='all')
                result = licenses.search_all_licenses(request)
                return self._process_suggest_result(result.results, entity_type)

            # elif entity_type == 'discipline':
            #     request = CurationSuggestSearchRequest(q='*', limit=limit, offset=0)
            #     result = disciplines.get_disciplines_suggestions(request)
            #     return self._process_suggest_result(result.results, entity_type)

            elif entity_type == 'learning_resource_type':
                request = CurationSuggestSearchRequest(q=None, limit=limit, offset=0)
                result = learning_resource_types.get_learning_resource_types_suggestions(request)
                return self._process_suggest_result(result, entity_type)

            elif entity_type == 'proficiency_level':
                request = CurationSuggestSearchRequest(q=None, limit=limit, offset=0)
                result = proficiency_levels.get_proficiency_levels_suggestions(request)
                return self._process_suggest_result(result, entity_type)

            elif entity_type == 'target_group':
                request = CurationSuggestSearchRequest(q=None, limit=limit, offset=0)
                result = target_groups.get_target_groups_suggestions(request)
                return self._process_suggest_result(result, entity_type)

            elif entity_type == 'media_type':
                request = CurationSuggestSearchRequest(q=None, limit=limit, offset=0)
                result = media_types.get_media_types_suggestions(request)
                return self._process_suggest_result(result, entity_type)

            elif entity_type == 'language':
                request = CurationSuggestSearchRequest(q='*', limit=limit, offset=0)
                result = languages.get_languages_suggestions(request)
                return self._process_suggest_result(result.results, entity_type)

            elif entity_type == 'community':
                request = CurationSuggestSearchRequest(q='*', limit=limit, offset=0)
                result = communities.get_communities_suggestions(request)
                return self._process_suggest_result(result.results, entity_type)

            else:
                self.logger.warning(f"No handler for entity type: {entity_type}")
                return []

        except Exception as e:
            self.logger.error(f"Error discovering entities of type {entity_type}: {e}")
            return []

    def _process_suggest_result(self, results: List, entity_type: str) -> List[Dict[str, Any]]:
        """
        Process suggest function results into standardized entity dictionaries.

        Args:
            results: List of result objects from suggest functions
            entity_type: Type of entity being processed

        Returns:
            List of standardized entity dictionaries
        """
        entities = []

        for item in results:
            entity_data = self._process_suggest_item(item, entity_type)
            if entity_data:
                entities.append(entity_data)

        self.logger.info(f"Processed {len(entities)} {entity_type} entities from suggest function")
        return entities

    def _process_suggest_item(self, item, entity_type: str) -> Optional[Dict[str, Any]]:
        """
        Process suggest result item into standardized entity dictionary.

        Args:
            item: Result item from suggest function (LabelValueItem or other types)
            entity_type: Type of entity being processed

        Returns:
            Standardized entity dictionary or None if invalid
        """
        try:
            # Handle different item types based on the suggest function
            if hasattr(item, 'value') and hasattr(item, 'label'):
                # LabelValueItem from learning_resource_types, media_types, proficiency_levels, target_groups
                fuseki_uri = item.value
                label = item.label

                # Try to extract UUID from URI (fragment or path segment)
                fuseki_uuid = self._extract_uuid_from_uri(fuseki_uri)
                if not fuseki_uuid:
                    # Fallback: generate UUID if we can't extract from URI
                    fuseki_uuid = str(uuid.uuid4())

                metadata = {'label': label}

            else:
                # Legacy handling for other item types (licenses, disciplines, communities)
                fuseki_uri = getattr(item, 'value', None) or getattr(item, 'uri', None) or getattr(item, 'id', None)
                if not fuseki_uri:
                    return None

                # Try to get UUID from item attribute first
                fuseki_uuid = getattr(item, 'uuid', None)
                if not fuseki_uuid:
                    # Try to extract UUID from URI (fragment or path segment)
                    fuseki_uuid = self._extract_uuid_from_uri(fuseki_uri)
                    if not fuseki_uuid:
                        # Fallback: generate UUID if we can't extract from URI
                        fuseki_uuid = str(uuid.uuid4())

                # Extract label/name based on entity type
                if entity_type == 'license':
                    label = getattr(item, 'licenseName', '') or getattr(item, 'label', '')
                else:
                    label = getattr(item, 'label', '') or getattr(item, 'name', '') or getattr(item, 'title', '')

                # Build metadata dictionary
                metadata = {'label': label}

                # Add entity-type-specific metadata
                if entity_type == 'license':
                    metadata.update({
                        'license_id': getattr(item, 'licenseId', ''),
                        'license_link': getattr(item, 'licenseLink', ''),
                        'description': getattr(item, 'licenseDescription', ''),
                    })
                # elif entity_type == 'discipline':
                #     metadata.update({
                #         'description': getattr(item, 'description', ''),
                #         'parent_id': getattr(item, 'parentId', ''),
                #     })
                elif entity_type == 'language':
                    # Extract language code from URI for duplicate detection
                    code = self._extract_language_code_from_uri(fuseki_uri)
                    metadata.update({
                        'code': code if code else '',
                        'uri': fuseki_uri,  # Add URI for Language model
                        'native_name': getattr(item, 'native_name', ''),
                    })
                elif entity_type == 'community':
                    metadata.update({
                        'description': getattr(item, 'description', ''),
                        'homepage': getattr(item, 'homepage', ''),
                    })
                else:
                    # Generic metadata for other types
                    metadata.update({
                        'description': getattr(item, 'description', ''),
                    })

            return {
                'entity_type': entity_type,
                'fuseki_uri': fuseki_uri,
                'fuseki_uuid': fuseki_uuid,
                'metadata': metadata
            }

        except Exception as e:
            self.logger.warning(f"Error processing suggest result for {entity_type}: {e}")
            return None

    def search_entities_by_query(self, entity_type: str, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for entities of a specific type using a text query.

        Args:
            entity_type: Type of entity to search
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching entity dictionaries
        """
        if entity_type not in self.SUPPORTED_ENTITY_TYPES:
            self.logger.warning(f"Unknown entity type: {entity_type}")
            return []

        try:
            # Call the appropriate suggest function with the query
            if entity_type == 'license':
                request = CurationSuggestLicensesRequest(q=query, limit=limit, offset=0, filter='all')
                result = licenses.search_all_licenses(request)
                return self._process_suggest_result(result.results, entity_type)

            # elif entity_type == 'discipline':
            #     request = CurationSuggestSearchRequest(q=query, limit=limit, offset=0)
            #     result = disciplines.get_disciplines_suggestions(request)
            #     return self._process_suggest_result(result.results, entity_type)

            elif entity_type == 'learning_resource_type':
                # Use None for wildcard search, otherwise use the actual query
                search_query = None if query == '*' else query
                request = CurationSuggestSearchRequest(q=search_query, limit=limit, offset=0)
                result = learning_resource_types.get_learning_resource_types_suggestions(request)
                return self._process_suggest_result(result, entity_type)

            elif entity_type == 'proficiency_level':
                # Use None for wildcard search, otherwise use the actual query
                search_query = None if query == '*' else query
                request = CurationSuggestSearchRequest(q=search_query, limit=limit, offset=0)
                result = proficiency_levels.get_proficiency_levels_suggestions(request)
                return self._process_suggest_result(result, entity_type)

            elif entity_type == 'target_group':
                # Use None for wildcard search, otherwise use the actual query
                search_query = None if query == '*' else query
                request = CurationSuggestSearchRequest(q=search_query, limit=limit, offset=0)
                result = target_groups.get_target_groups_suggestions(request)
                return self._process_suggest_result(result, entity_type)

            elif entity_type == 'media_type':
                # Use None for wildcard search, otherwise use the actual query
                search_query = None if query == '*' else query
                request = CurationSuggestSearchRequest(q=search_query, limit=limit, offset=0)
                result = media_types.get_media_types_suggestions(request)
                return self._process_suggest_result(result, entity_type)

            elif entity_type == 'language':
                request = CurationSuggestSearchRequest(q=query, limit=limit, offset=0)
                result = languages.get_languages_suggestions(request)
                return self._process_suggest_result(result.results, entity_type)

            elif entity_type == 'community':
                request = CurationSuggestSearchRequest(q=query, limit=limit, offset=0)
                result = communities.get_communities_suggestions(request)
                return self._process_suggest_result(result.results, entity_type)

            else:
                self.logger.warning(f"No search handler for entity type: {entity_type}")
                return []

        except Exception as e:
            self.logger.error(f"Error searching {entity_type} entities: {e}")
            return []

    def get_entity_by_uri(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific entity by its URI.
        This method tries to find the entity by searching through different entity types.

        Args:
            uri: The RDF URI of the entity

        Returns:
            Entity dictionary or None if not found
        """
        # Try to search for the entity in all supported entity types
        for entity_type in self.SUPPORTED_ENTITY_TYPES:
            try:
                # Extract a search term from the URI (use the fragment or last part)
                if '#' in uri:
                    search_term = uri.split('#')[-1]
                elif '/' in uri:
                    search_term = uri.split('/')[-1]
                else:
                    search_term = uri

                # Search for entities matching this term
                entities = self.search_entities_by_query(entity_type, search_term, limit=50)

                # Look for exact URI match
                for entity in entities:
                    if entity.get('fuseki_uri') == uri:
                        return entity

            except Exception as e:
                self.logger.debug(f"Error searching for URI {uri} in {entity_type}: {e}")
                continue

        self.logger.warning(f"Entity not found for URI: {uri}")
        return None

    def count_entities_by_type(self, entity_type: str) -> int:
        """
        Count the number of entities of a specific type in Fuseki.

        Args:
            entity_type: Type of entity to count

        Returns:
            Number of entities found
        """
        try:
            entities = self.discover_all_entities_by_type(entity_type, limit=10000)
            return len(entities)
        except Exception as e:
            self.logger.error(f"Error counting entities of type {entity_type}: {e}")
            return 0

    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """
        Check if a string is a valid UUID format.

        Args:
            uuid_string: String to check

        Returns:
            True if valid UUID format, False otherwise
        """
        try:
            uuid.UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            return False

    def _extract_uuid_from_uri(self, uri: str) -> Optional[str]:
        """
        Extract UUID from URI (checks both fragment and path segments).

        Handles URIs like:
          - https://id.dalia.education/community/fa16b39f-4bc1-4f48-beaf-cbd030d5a7b4
          - http://example.org#fa16b39f-4bc1-4f48-beaf-cbd030d5a7b4
          - http://example.org/resource/fa16b39f-4bc1-4f48-beaf-cbd030d5a7b4#details

        Args:
            uri: URI to extract UUID from

        Returns:
            UUID string or None if not found
        """
        if not uri:
            return None

        # First check fragment (after #)
        if '#' in uri:
            fragment = uri.split('#')[-1]
            if self._is_valid_uuid(fragment):
                return fragment

        # Then check all path segments (split by /)
        parts = uri.rstrip('/').split('/')
        for part in reversed(parts):  # Check from end to start
            # Remove fragment if present
            if '#' in part:
                part = part.split('#')[0]
            if part and self._is_valid_uuid(part):
                return part

        return None

    def _extract_language_code_from_uri(self, uri: str) -> Optional[str]:
        """
        Extract language code from Lexvo URI.

        Examples:
          http://lexvo.org/id/iso639-3/aar -> aar
          http://lexvo.org/id/iso639-1/en -> en

        Args:
            uri: Lexvo URI

        Returns:
            Language code or None
        """
        if not uri:
            return None

        import re
        # Pattern: http://lexvo.org/id/iso639-X/CODE
        match = re.search(r'/iso639-[0-9]/([a-zA-Z]{2,3})$', uri)
        if match:
            return match.group(1).lower()

        # Try extracting last segment as fallback
        parts = uri.rstrip('/').split('/')
        if parts:
            last_part = parts[-1]
            # Validate it looks like a language code (2-3 letters)
            if re.match(r'^[a-zA-Z]{2,3}$', last_part):
                return last_part.lower()

        return None