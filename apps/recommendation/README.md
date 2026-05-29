# recommendation (DISABLED)

This app is disabled pending Fuseki/SPARQL infrastructure setup.
It is NOT in INSTALLED_APPS and has no active migrations or URL routes.

To enable:
1. Ensure the 'search' app is enabled (recommendation depends on it)
2. Add 'recommendation' to INSTALLED_APPS in config/settings/base.py
3. Run: make makemigrations && make migrate
4. Wire URLs in config/urls.py
