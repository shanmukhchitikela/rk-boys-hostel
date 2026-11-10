from .context import reset_current_actor, set_current_actor


class AuditActorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        actor = user if user and user.is_authenticated else None
        token = set_current_actor(actor)
        try:
            return self.get_response(request)
        finally:
            reset_current_actor(token)