# search (DISABLED)

This app is disabled pending Fuseki/SPARQL infrastructure setup.
It is NOT in INSTALLED_APPS and has no active migrations or URL routes.

To enable:
1. Add Fuseki service to podman-compose.yml
2. Add 'search' to INSTALLED_APPS in config/settings/base.py
3. Run: make makemigrations && make migrate
4. Wire URLs in config/urls.py
