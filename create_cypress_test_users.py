from users.models import User

def create_cypress_test_users():
    # Dealer user
    dealer, _ = User.objects.update_or_create(
        username='dealeruser',
        defaults={
            'email': 'dealer@example.com',
            'first_name': 'Dealer',
            'last_name': 'Test',
            'user_type': 'dealer',
            'is_active': True,
        }
    )
    dealer.set_password('testpassword123')
    dealer.save()

    # Shopkeeper user
    shopkeeper, _ = User.objects.update_or_create(
        username='shopkeeperuser',
        defaults={
            'email': 'shopkeeper@example.com',
            'first_name': 'Shopkeeper',
            'last_name': 'Test',
            'user_type': 'shopkeeper',
            'is_active': True,
        }
    )
    shopkeeper.set_password('testpassword123')
    shopkeeper.save()

    # General test user
    testuser, _ = User.objects.update_or_create(
        username='testuser',
        defaults={
            'email': 'testuser@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'shopkeeper',
            'is_active': True,
        }
    )
    testuser.set_password('testpassword123')
    testuser.save()

create_cypress_test_users()
print('Cypress test users created.')
