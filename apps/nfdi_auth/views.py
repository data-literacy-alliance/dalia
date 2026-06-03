from allauth.account.internal.decorators import login_not_required
from allauth.account.views import LoginView
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView
from allauth.socialaccount.providers.openid_connect.views import OpenIDConnectOAuth2Adapter
from django.contrib.admin import site as admin_site
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.http import Http404
from django.shortcuts import redirect, render
from two_factor.views import LoginView as TwoFactorLoginView


class CustomLoginView(LoginView):
    template_name = "account/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site = get_current_site(self.request)

        enriched_providers = []
        seen_ids = set()

        # Iterate over configured SocialApp objects directly — avoids registry duplicates
        for app in SocialApp.objects.filter(sites=site):
            # For OIDC apps, provider_id is a per-app slug (e.g. "iam4nfdi")
            oidc_id = getattr(app, "provider_id", None) or app.provider
            if oidc_id in seen_ids:
                continue
            seen_ids.add(oidc_id)

            logo_url = app.settings.get("logo_url") if app.settings else None

            # Build the correct login URL for this provider type
            if app.provider == "openid_connect":
                login_url = f"/accounts/oidc/{oidc_id}/login/?process=login"
            else:
                login_url = f"/accounts/{app.provider}/login/?process=login"

            enriched_providers.append(
                {
                    "id": oidc_id,
                    "name": app.name,
                    "logo_url": logo_url,
                    "url": login_url,
                }
            )

        context["custom_social_providers"] = enriched_providers
        return context


class NFDIOpenIDConnectAdapter(OpenIDConnectOAuth2Adapter):
    """
    Custom OIDC adapter. Returns the hardcoded production callback URL when the
    request host is localhost or the IONOS routing hostname (dalia-*).

    IONOS replaces the browser's Host header (search.dalia.education) with the
    internal routing hostname at the gateway level. Same fix as daliaproject/prod.

    allauth 65.16.1 changed basic_auth to prefer client_secret_post when both methods
    are advertised — IAM4NFDI only accepts client_secret_basic despite advertising both.
    """

    @property
    def basic_auth(self):
        # allauth 65.16.1 returns False when client_secret_post is also listed in
        # token_endpoint_auth_methods_supported. IAM4NFDI advertises both but only
        # accepts client_secret_basic — force it here.
        return True

    def get_callback_url(self, request, app):
        host = request.get_host()
        if "search.dalia.education" in host or host.startswith("dalia-"):
            return "https://search.dalia.education/accounts/oidc/iam4nfdi/login/callback/"
        # localhost: standard allauth builds http://localhost/... which IAM4NFDI rejects;
        # use the production URL so the redirect reaches the registered callback.
        if host.split(":")[0] == "localhost":
            return "https://search.dalia.education/accounts/oidc/iam4nfdi/login/callback/"
        return super().get_callback_url(request, app)


@login_not_required
def nfdi_oidc_login(request, provider_id):
    """OIDC login — forces the callback URL via NFDIOpenIDConnectAdapter.

    provider.redirect_from_request() creates its own default adapter internally,
    bypassing get_callback_url. Patching provider.get_oauth2_adapter ensures our
    adapter is used and the correct redirect_uri is sent to IAM4NFDI.
    """
    try:
        adapter = NFDIOpenIDConnectAdapter(request, provider_id)
        provider = adapter.get_provider()
        provider.get_oauth2_adapter = lambda req: NFDIOpenIDConnectAdapter(
            req, provider.app.provider_id
        )
        return provider.redirect_from_request(request)
    except SocialApp.DoesNotExist:
        raise Http404


@login_not_required
def nfdi_oidc_callback(request, provider_id):
    """OIDC callback — uses NFDIOpenIDConnectAdapter to ensure correct Basic Auth."""
    try:
        view = OAuth2CallbackView.adapter_view(NFDIOpenIDConnectAdapter(request, provider_id))
        return view(request)
    except SocialApp.DoesNotExist:
        raise Http404


class AdminStyledTwoFactorLoginView(TwoFactorLoginView):
    """two_factor LoginView with Unfold admin context injected.
    Provides colors, styles, site_title etc. so the /account/login/ page
    renders with the same styling as the standard Unfold admin login.
    """

    # Unfold input CSS classes (matches UnfoldAdminTextInputWidget)
    _INPUT_CLASSES = (
        "border border-base-200 bg-white font-medium placeholder-base-400 "
        "rounded-default shadow-xs text-font-default-light text-sm "
        "focus:outline-2 focus:-outline-offset-2 focus:outline-primary-600 "
        "group-[.errors]:border-red-600 "
        "dark:bg-base-900 dark:border-base-700 dark:text-font-default-dark "
        "dark:group-[.errors]:border-red-500 "
        "px-3 py-2 w-full"
    )

    def get_form(self, step=None, **kwargs):
        form = super().get_form(step=step, **kwargs)
        for field in form.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{self._INPUT_CLASSES} {existing}".strip()
        return form

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        context.update(admin_site.each_context(self.request))
        return context


@login_required
def profile_view(request):
    last_provider = request.session.get("last_social_provider")
    sa = None

    if last_provider:
        sa = SocialAccount.objects.filter(user=request.user, provider=last_provider).first()

    claims = sa.extra_data if sa else {}

    # Optional: include tokens
    token = SocialToken.objects.filter(account=sa).first() if sa else None
    if token:
        claims = {
            **claims,
            "access_token": token.token,
            "refresh_token": token.token_secret,
            "expires_at": token.expires_at,
        }

    # Update name if not already filled in
    updated = False
    if claims.get("given_name") and not request.user.first_name:
        request.user.first_name = claims["given_name"]
        updated = True
    if claims.get("family_name") and not request.user.last_name:
        request.user.last_name = claims["family_name"]
        updated = True
    if updated:
        request.user.save(update_fields=["first_name", "last_name"])

    return redirect("/profile/contributions/")
