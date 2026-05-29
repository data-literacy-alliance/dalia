"""
ASGI config for Work Track Pro.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

# Add apps/ directory to sys.path for cleaner imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "apps"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_asgi_application()
