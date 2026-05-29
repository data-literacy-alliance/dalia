# entity_mapping (DISABLED)

This app is disabled pending Fuseki/SPARQL infrastructure setup.
It is NOT in INSTALLED_APPS and has no active migrations or URL routes.

To enable:
1. Add Fuseki service to podman-compose.yml
2. Add 'entity_mapping' to INSTALLED_APPS in config/settings/base.py
3. Run: make makemigrations && make migrate
4. Wire admin URLs if needed

Note: migrations/ directory from legacy dalia is intentionally excluded.
Re-generate migrations after enabling via: make makemigrations
