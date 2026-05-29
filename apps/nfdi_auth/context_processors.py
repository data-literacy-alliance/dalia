from allauth.socialaccount.models import SocialAccount, SocialToken


def nfdi_claims(request):
    """
    Adds the provider's JSON claims to every template context.
    Falls back gracefully if the user (or account) is absent.
    """
    if not request.user.is_authenticated:
        return {}

    try:
        last_provider = request.session.get("last_social_provider")
        sa = None

        if last_provider:
            sa = SocialAccount.objects.get(
                user=request.user, provider=last_provider
            ) if last_provider else None

        if not sa:
            return {}

        claims = dict(sa.extra_data)

        # Optional: include token metadata - for dev purposes
        token = SocialToken.objects.filter(account=sa).first()
        if token:
            claims.update({
                "access_token": token.token,
                "refresh_token": token.token_secret,
                "expires_at": token.expires_at,
            })

        return {"nfdi_claims": sa.extra_data}
    except SocialAccount.DoesNotExist:
        return {}
