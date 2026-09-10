"""
Base settings for ICZ.
Shared configuration for all environments.
"""

from pathlib import Path

import environ
from django.templatetags.static import static

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    POSTGRES_PORT=(int, 5432),
    GUNICORN_WORKERS=(int, 3),
    GUNICORN_TIMEOUT=(int, 60),
    ELASTICSEARCH_HOST=(str, "elasticsearch:9200"),
    ELASTICSEARCH_USER=(str, ""),
    ELASTICSEARCH_PASSWORD=(str, ""),
    IAM4NFDI_CLIENT_ID=(str, ""),
    IAM4NFDI_CLIENT_SECRET=(str, ""),
    CORS_ALLOWED_ORIGINS=(list, []),
    DALIA_TRIPLESTORE_BASE_URL=(str, "http://daliaproject_prod-fuseki_1:3030/"),
)

# Read .env file if it exists
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY", default="change-me-to-a-random-50-char-string")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Reverse proxy: trust X-Forwarded-Proto from nginx / Traefik.
# Required so allauth builds https:// redirect_uris correctly when behind a proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Reverse proxy: use X-Forwarded-Host so request.get_host() returns the public hostname.
USE_X_FORWARDED_HOST = True

# Custom User Model (must be set before any migration)
AUTH_USER_MODEL = "users.User"

# Application definition
INSTALLED_APPS = [
    # Django Unfold (must be before django.contrib.admin)
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    # Django core apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.postgres",
    # Third-party apps
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "drf_spectacular",
    "import_export",
    "django_tasks",
    "axes",
    "rest_framework_simplejwt.token_blacklist",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "two_factor",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.openid_connect",
    "allauth.headless",
    "django_elasticsearch_dsl",
    "django_elasticsearch_dsl_drf",
    "taggit",
    "sortedm2m",
    # DALIA apps
    "core",
    "pages",
    "users",
    "curation",
    "account_deletion",
    "nfdi_auth",
    "api",
    # Search + GraphDB apps (Fuseki-backed)
    "search",
    "recommendation",
    "entity_mapping",
]

# Django Sites Framework (required by allauth)
SITE_ID = 1

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "nfdi_auth.context_processors.nfdi_claims",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Password hashers (Argon2 recommended)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# Authentication backends (django-axes)
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Login/Logout redirects
LOGIN_REDIRECT_URL = "/profile/"  # Redirect to profile after login (same as old production)
LOGOUT_REDIRECT_URL = "/"  # Redirect to home after logout

# CSRF Settings
# Add your public domain(s) to CSRF_TRUSTED_ORIGINS in .env, e.g.:
#   CSRF_TRUSTED_ORIGINS=https://your-domain.example.com
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:7080",
        "http://localhost:7087",
    ],
)

# Internationalization
LANGUAGE_CODE = env("LANGUAGE_CODE", default="en-us")
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"

# Where Django LOOKS for static files (source files)
STATICFILES_DIRS = [
    BASE_DIR / "static",  # Project-wide static folder
]

# Where Django PUTS collected files (via collectstatic)
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (user uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cache Configuration (Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
        "KEY_PREFIX": "dalia20",
        "TIMEOUT": 300,  # 5 minutes default
    }
}

# Session Configuration (Redis)
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    "TITLE": "DALIA 2.0 API",
    "DESCRIPTION": "DALIA 2.0 OER Curation Platform API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
}

# Django Axes (brute-force protection)
from datetime import timedelta  # noqa: E402

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_RESET_ON_SUCCESS = True
AXES_LOCK_OUT_AT_FAILURE = True
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]

# Django Import/Export
IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_SKIP_ADMIN_LOG = False
IMPORT_EXPORT_TMP_STORAGE_CLASS = "import_export.tmp_storages.TempFolderStorage"
IMPORT_EXPORT_ESCAPE_FORMULAE_ON_EXPORT = True  # Security: prevent CSV injection

# Django Unfold
UNFOLD = {
    "SITE_TITLE": "DALIA 2.0",
    "SITE_HEADER": "DALIA 2.0",
    "SITE_URL": "/",
    "SITE_ICON": None,
    "SITE_LOGO": None,
    "SITE_SYMBOL": "speed",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_TIME_ZONE_WARNING": False,  # Disable "You are X hours ahead of server time" warning
    "SHOW_ALL_APPLICATIONS": True,
    "ENVIRONMENT": "config.settings.base.environment_callback",
    "DASHBOARD_CALLBACK": "config.settings.base.dashboard_callback",
    "THEME": None,  # None = allow user to toggle, "dark" = force dark, "light" = force light
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "192 132 252",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
    },
    "STYLES": [
        lambda request: static("css/admin_custom.css"),  # Use Django static() for proper resolution
    ],
}


def environment_callback(request):
    """Return environment badge for unfold admin."""
    if DEBUG:
        return ["Development", "warning"]
    return ["Production", "success"]


def dashboard_callback(request, context):
    """Minimal dashboard callback stub."""
    return context


# CORS Configuration
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:8080",
        "http://localhost:8000",
        "http://localhost:7080",
        "http://127.0.0.1:8080",
    ],
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# Elasticsearch Configuration
ELASTICSEARCH_DSL = {
    "default": {
        "hosts": env("ELASTICSEARCH_HOST", default="elasticsearch:9200"),
        "http_auth": (
            env("ELASTICSEARCH_USER", default=""),
            env("ELASTICSEARCH_PASSWORD", default=""),
        )
        if env("ELASTICSEARCH_USER", default="")
        else None,
    },
}

# SPARQL / Triplestore Configuration
DALIA_TRIPLESTORE_BASE_URL = env("DALIA_TRIPLESTORE_BASE_URL")

# Search sources — which producers feed POST /api/dalia/v1/items/.
# Transition path: ["fuseki"] -> ["fuseki","postgres"] -> ["postgres"].
# Default ["fuseki"] keeps current behavior (no-op). Env override is comma-separated, e.g. DALIA_SEARCH_SOURCES=fuseki,postgres
DALIA_SEARCH_SOURCES = env.list("DALIA_SEARCH_SOURCES", default=["fuseki", "postgres"])

# Login URL — points to django-two-factor-auth login (accepts username, used by admin).
# allauth login (email-based) stays at /accounts/login/ and is separate.
LOGIN_URL = "/account/login/"

# NFDI AAI / django-allauth Configuration
SOCIALACCOUNT_ADAPTER = "nfdi_auth.adapter.NFDISocialAdapter"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True

SOCIALACCOUNT_OPENID_CONNECT_CLIENT_ID = env("IAM4NFDI_CLIENT_ID", default="")
SOCIALACCOUNT_OPENID_CONNECT_CLIENT_SECRET = env("IAM4NFDI_CLIENT_SECRET", default="")

# OIDC app is configured via the database (Admin → Social accounts → Social applications).
# Do NOT define APPS here — that would duplicate the DB entry and cause MultipleObjectsReturned.
SOCIALACCOUNT_PROVIDERS = {}
