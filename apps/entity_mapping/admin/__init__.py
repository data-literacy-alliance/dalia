"""
Modular admin configuration for entity_mapping app.

This package organizes the 908-line admin.py into logical modules:
- mappings.py: EntityMappingAdmin (main admin, 805 lines)
- logs.py: SyncLogAdmin (112 lines)

PostgreSQL ↔ Fuseki Synchronization
------------------------------------
This app manages bidirectional synchronization between PostgreSQL and Apache Fuseki:

1. **Entity Mapping**: Tracks relationships between PostgreSQL UUIDs and Fuseki URIs
2. **Import Candidates**: Discover and import entities from Fuseki into PostgreSQL
3. **Sync Status**: Track synchronization state (pending, synced, failed)
4. **Sync Direction**: Control data flow (to_fuseki, to_postgresql, bidirectional)
5. **Audit Logging**: Complete sync history with success/failure tracking

Service Layer Architecture:
- import_candidate_service.py: Discover entities in Fuseki for import
- fuseki_query_service.py: SPARQL queries and Fuseki communication
- entity_creation_service.py: Create PostgreSQL entities from Fuseki data
- transformation_service.py: Data transformation between formats

Admin Features:
- Import candidate discovery and approval workflow
- Bulk sync operations (to Fuseki, to PostgreSQL)
- Custom admin views for candidate management
- Sync status visualization with color-coded badges
- Fuseki URI previews with links
- Metadata preview in JSON format
- Age tracking for stale mappings
"""

# Import all admin modules to register them with Django
from .mappings import *  # noqa
from .logs import *  # noqa
