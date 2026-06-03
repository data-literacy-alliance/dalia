import logging
import os

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

logger = logging.getLogger("allauth")


class NFDISocialAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        """
        Map provider claims to Django-User fields.
        Called *before* the User is saved by allauth.
        """
        logger.debug(f"OIDC Claims: {data}")

        user = super().populate_user(request, sociallogin, data)
        user.first_name = data.get("given_name", "")
        user.last_name = data.get("family_name", "")
        user.email = data.get("email", "")
        return user  # allauth does the save()

    def pre_social_login(self, request, sociallogin):
        """
        Connect social account to existing Django user with matching email.
        Prevents duplicate accounts when users login via NFDI with same email
        as an existing account.
        """
        if sociallogin.is_existing:
            return

        try:
            email = sociallogin.email_addresses[0].email if sociallogin.email_addresses else None
            if not email:
                logger.debug("No email found in social login")
                return

            from django.contrib.auth import get_user_model

            user_model = get_user_model()

            # Find existing user with this email (case-insensitive)
            existing_user = user_model.objects.get(email__iexact=email)
            sociallogin.connect(request, existing_user)
            logger.info(f"Connected social account to existing user: {email}")

        except user_model.DoesNotExist:
            logger.debug(f"No existing user found for email: {email}, will create new user")
            pass
        except user_model.MultipleObjectsReturned:
            logger.warning(f"Multiple users found with email: {email}, using first match")
            existing_user = user_model.objects.filter(email__iexact=email).first()
            sociallogin.connect(request, existing_user)
        except Exception as e:
            logger.error(f"Error in pre_social_login: {e}")
            pass

    def get_login_redirect_url(self, request):
        """Redirect to appropriate frontend domain after NFDI login."""
        host = request.get_host()

        if "admin-dev" in host:
            base = os.environ.get("DEV_FRONTEND_URL", "")
            return base + "/profile/" if base else "/profile/"
        elif "admin-staging" in host or "admin-stage" in host:
            base = os.environ.get("STAGING_FRONTEND_URL", "")
            return base + "/profile/" if base else "/profile/"
        elif "search.dalia.education" in host or "admin-prod" in host:
            return "https://search.dalia.education/profile/"
        else:
            return "/profile/"
