from django.conf import settings


class ForceDomainMiddleware:
    """
    Override HTTP_HOST and HTTP_X_FORWARDED_HOST with SITE_DOMAIN.

    IONOS routing replaces the original browser Host (search.dalia.education)
    with the internal routing hostname. No incoming header carries the real domain,
    so it must be configured explicitly via the SITE_DOMAIN env var.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.site_domain = getattr(settings, "SITE_DOMAIN", "")

    def __call__(self, request):
        if self.site_domain:
            request.META["HTTP_HOST"] = self.site_domain
            request.META["HTTP_X_FORWARDED_HOST"] = self.site_domain
        return self.get_response(request)
