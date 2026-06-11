"""
URL configuration for DALIA 2.0.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

import two_factor.urls as _tf_urls

from apps.core.views import admin_logout
from nfdi_auth.views import (
    AdminStyledTwoFactorLoginView,
    CustomLoginView,
    nfdi_oidc_callback,
    nfdi_oidc_login,
)
from search.views_sparql_proxy import SPARQLProxyView

urlpatterns = [
    # Custom admin logout (handles CSRF properly)
    path("admin/logout/", admin_logout, name="admin_logout"),
    # Admin panel
    path("admin/", admin.site.urls),
    # two_factor login at /account/login/ — Unfold-styled, accepts username (used by admin redirect)
    path("account/login/", AdminStyledTwoFactorLoginView.as_view(), name="two_factor_login"),
    # remaining two_factor URLs (OTP device management, QR setup, etc.)
    path("", include(_tf_urls.urlpatterns)),
    # Override OIDC login with custom adapter (localhost callback URL fix + DB-derived URL)
    path("accounts/oidc/<str:provider_id>/login/", nfdi_oidc_login, name="openid_connect_login"),
    # Override OIDC callback with custom adapter (must come before allauth.urls)
    path(
        "accounts/oidc/<str:provider_id>/login/callback/",
        nfdi_oidc_callback,
        name="openid_connect_callback",
    ),
    # Override allauth login with CustomLoginView to inject custom_social_providers context
    path("accounts/login/", CustomLoginView.as_view(), name="account_login"),
    # Authentication URLs (login, logout, password reset)
    path("accounts/", include("allauth.urls")),
    # NFDI auth views (CustomLoginView, profile)
    path("", include("nfdi_auth.urls")),
    # API v1 — core health/auth endpoints
    path("api/v1/", include("core.urls")),
    # API v1 — DALIA app endpoints (stub until S-6)
    path("api/v1/", include("api.urls")),
    # Pages (managed static content — privacy policy, etc.)
    path("api/v1/pages/", include("pages.urls")),
    # API aliases without /v1/ prefix — frontend calls /api/auth/... (no /v1/)
    path("api/", include("core.urls")),
    path("api/", include("api.urls")),
    # GraphDB/Fuseki search endpoints
    path("api/dalia/", include("search.urls")),
    path("api/dalia/recommendation/", include("recommendation.urls")),
    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/doc/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui-doc"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # SPARQL Explorer proxy (read-only, replaces Next.js /sparql-api route)
    path("sparql-api", SPARQLProxyView.as_view(), name="sparql-proxy"),
]
