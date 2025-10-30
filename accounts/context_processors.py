from typing import Dict, Any


def user_profile(request) -> Dict[str, Any]:
    """Inject the authenticated user's profile (if any) as USER_PROFILE.

    Uses get_or_create to avoid reverse OneToOne DoesNotExist errors and to
    ensure a profile exists after first authenticated request.
    """
    profile = None
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        try:
            from .models import UserProfile  # local import to avoid app load order issues
            profile, _ = UserProfile.objects.get_or_create(user=user)
        except Exception:
            profile = None
    return {"USER_PROFILE": profile}

