from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
import os
import django

# Set up django if used in asgi before registry is ready
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kirana.settings')

@database_sync_to_async
def get_user_from_token(token_key):
    try:
        from rest_framework.authtoken.models import Token
        return Token.objects.select_related('user').get(key=token_key).user
    except Exception:
        return AnonymousUser()

class TokenAuthMiddleware:
    """
    Custom middleware for Channels that reads DRF tokens from the 'token' query parameter.
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        from urllib.parse import parse_qs
        
        # Get token from query string
        query_params = parse_qs(scope["query_string"].decode())
        token_key = query_params.get("token", [None])[0]
        
        if token_key:
            scope["user"] = await get_user_from_token(token_key)
        else:
            scope["user"] = AnonymousUser()
            
        return await self.inner(scope, receive, send)
