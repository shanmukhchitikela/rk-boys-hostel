from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseForbidden

ROLE_GROUPS = ("Owner", "Manager", "Warden")


def user_has_role(user, *roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


def role_required(*roles):
    if not roles:
        raise ImproperlyConfigured("role_required must be given at least one role.")

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            if not user_has_role(request.user, *roles):
                return HttpResponseForbidden("You do not have permission to access this page.")
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator