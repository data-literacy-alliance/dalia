# api/utils/jwt.py
from allauth.socialaccount.models import SocialAccount


def custom_jwt_payload(user):
    try:
        sa = SocialAccount.objects.filter(user=user).first()
        extra = sa.extra_data if sa else {}
    except Exception:
        extra = {}

    return {
        "user_id": user.id,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "name": f"{user.first_name} {user.last_name}".strip(),
        "given_name": user.first_name,
        "family_name": user.last_name,
        "sub": extra.get("sub"),
        "voperson_id": extra.get("voperson_id", []),
        "voperson_external_affiliation": extra.get("voperson_external_affiliation", []),
    }
