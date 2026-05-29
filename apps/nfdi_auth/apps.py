from django.apps import AppConfig


class NFDIAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nfdi_auth"
    verbose_name = "NFDI AAI Authentication"

    def ready(self):
        import nfdi_auth.signals  # noqa: F401
        from allauth.socialaccount.providers.openid_connect.views import (
            OpenIDConnectOAuth2Adapter,
        )

        original = OpenIDConnectOAuth2Adapter.get_callback_url

        def custom_cb(self, request, app):
            if app.provider_id == "iam4nfdi":
                host = request.get_host()
                # Production domain or IONOS routing hostname (dalia-*) both map to
                # the registered production callback URL — same logic as daliaproject/prod.
                if "search.dalia.education" in host or host.startswith("dalia-"):
                    return "https://search.dalia.education/accounts/oidc/iam4nfdi/login/callback/"
                # Localhost / other environments: use dynamic URL
                scheme = "https" if request.is_secure() else "http"
                return f"{scheme}://{host}/accounts/oidc/iam4nfdi/login/callback/"

            return original(self, request, app)

        OpenIDConnectOAuth2Adapter.get_callback_url = custom_cb

        # allauth 65.16.1 changed basic_auth: returns False when client_secret_post is also
        # in token_endpoint_auth_methods_supported. IAM4NFDI advertises both but only accepts
        # client_secret_basic — force Basic Auth for the iam4nfdi provider.
        _original_basic_auth = OpenIDConnectOAuth2Adapter.basic_auth.fget

        def custom_basic_auth(self):
            try:
                if self.get_provider().app.provider_id == "iam4nfdi":
                    return True
            except Exception:
                pass
            return _original_basic_auth(self)

        OpenIDConnectOAuth2Adapter.basic_auth = property(custom_basic_auth)
