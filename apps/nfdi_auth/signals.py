import logging

from allauth.account.signals import user_logged_in
from allauth.socialaccount.signals import social_account_added, social_account_updated
from django.apps import apps
from django.dispatch import receiver

logger = logging.getLogger("allauth")


def _extract_names(extra_data: dict) -> tuple[str, str]:
    """Return (given_name, family_name) from extra_data, handling both
    the old flat format and the new allauth v65+ nested-userinfo format."""
    userinfo = extra_data.get("userinfo") or extra_data
    return userinfo.get("given_name", ""), userinfo.get("family_name", "")


@receiver([social_account_added, social_account_updated])
def update_names(sender, request, sociallogin, **kw):
    """Update Django User first_name/last_name from NFDI claims on each login."""
    claims = sociallogin.account.extra_data
    user = sociallogin.user
    changed = False

    fn, ln = _extract_names(claims)

    if fn and user.first_name != fn:
        user.first_name = fn
        changed = True
    if ln and user.last_name != ln:
        user.last_name = ln
        changed = True
    if changed:
        user.save(update_fields=["first_name", "last_name"])


@receiver([social_account_added, social_account_updated])
def sync_person_from_nfdi(sender, request, sociallogin, **kwargs):
    """
    Create or update Person profile after NFDI login.

    Syncs all available NFDI AAI data to Person model:
    - first_name from given_name
    - last_name from family_name

    Fields NOT available in NFDI (left blank for user to fill manually):
    - orcid, homepage, uri
    """
    if sociallogin.account.provider != "iam4nfdi":
        logger.debug(
            f"Skipping Person sync - not NFDI login "
            f"(provider: {sociallogin.account.provider})"
        )
        return

    user = sociallogin.user
    claims = sociallogin.account.extra_data

    logger.debug(
        f"sync_person_from_nfdi triggered for user: {user.username} (ID: {user.id})"
    )
    logger.debug(f"NFDI Claims received: {claims}")

    try:
        Person = apps.get_model("curation", "Person")
    except LookupError:
        logger.error("Person model not found - cannot sync profile")
        return

    first_name, last_name = _extract_names(claims)

    if not first_name and not last_name:
        logger.warning(
            f"No names available for user {user.username} - skipping Person sync. "
            f"Claims keys: {list(claims.keys())}"
        )
        return

    try:
        person, created = Person.objects.get_or_create(
            user=user,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                # orcid, homepage, uri: blank — user fills manually
                "privacy_level": "private",  # Default: user must explicitly go public
                "email_notifications": True,
            },
        )

        if not created:
            updated = False

            if person.first_name != first_name:
                person.first_name = first_name
                updated = True

            if person.last_name != last_name:
                person.last_name = last_name
                updated = True

            if updated:
                person.save(update_fields=["first_name", "last_name", "modified"])
                logger.info(
                    f"Updated Person for user {user.username}: "
                    f"{first_name} {last_name}"
                )
            else:
                logger.debug(f"Person already up-to-date for user {user.username}")
        else:
            logger.info(
                f"Created Person for user {user.username}: {first_name} {last_name}"
            )

    except Exception as e:
        logger.error(
            f"Error syncing Person for user {user.username}: {e}", exc_info=True
        )


@receiver(user_logged_in)
def store_provider_in_session(request, user, **kwargs):
    """Store the last used social provider in the session for context processors."""
    sociallogin = kwargs.get("sociallogin")
    if sociallogin is None:
        return
    try:
        provider = sociallogin.account.provider
        request.session["last_social_provider"] = provider
        logger.debug(f"Stored last used social provider: {provider}")
    except Exception as e:
        logger.warning(f"Could not store provider in session: {e}")
