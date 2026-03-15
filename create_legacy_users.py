import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kirana.settings')
django.setup()

from users.models import User
from rest_framework.authtoken.models import Token

def create_legacy_user(username, user_type):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': f'{username}@example.com',
            'user_type': user_type,
            'first_name': 'Legacy',
            'last_name': user_type.capitalize()
        }
    )
    if created:
        user.set_password('Password123!')
        user.save()
    
    token, _ = Token.objects.get_or_create(user=user)
    print(f"CREATED_USER:{username}")
    print(f"TOKEN:{token.key}")
    print(f"USER_TYPE:{user_type}")

if __name__ == "__main__":
    create_legacy_user('legacy_shopkeeper', 'shopkeeper')
    create_legacy_user('legacy_dealer', 'dealer')
