from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from .models import User
from .serializers import (
    UserSerializer, UserRegistrationSerializer,
    UserLoginSerializer, UserProfileSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """User management ViewSet"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [TokenAuthentication]
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user's profile"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'user': UserSerializer(user).data,
                    'token': token.key,
                    'message': 'User registered successfully'
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                import traceback
                return Response({
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Standalone login API
class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
            if user is not None:
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'user': UserSerializer(user).data,
                    'token': token.key,
                    'message': 'Login successful'
                }, status=status.HTTP_200_OK)
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        try:
            request.user.auth_token.delete()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except (AttributeError, Token.DoesNotExist):
            return Response({'detail': 'Token not found'}, status=status.HTTP_400_BAD_REQUEST)


class GoogleAuthAPIView(APIView):
    """
    Accepts a Firebase ID token from the frontend, verifies it with Google,
    and returns a DRF auth token.
    
    Flow:
    1. Frontend signs-in with Google via Firebase SDK and gets an ID token.
    2. Frontend POSTs that ID token here.
    3. Backend verifies the token, finds or creates the user, returns DRF token.
    
    For first-time Google users, a `user_type` field must also be sent.
    If the user already exists, `user_type` is ignored.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        id_token_str = request.data.get('id_token')
        user_type = request.data.get('user_type')  # Required for first-time signup

        if not id_token_str:
            return Response({'detail': 'id_token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the Firebase ID token using Google's public certificates
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests

            # FIREBASE_PROJECT_ID must match your Firebase project
            import os
            firebase_project_id = os.environ.get('FIREBASE_PROJECT_ID', '')
            
            # Verify token (audience can be the web client ID or project ID)
            idinfo = id_token.verify_firebase_token(
                id_token_str,
                google_requests.Request(),
                audience=firebase_project_id if firebase_project_id else None
            )
        except ValueError as e:
            return Response({'detail': f'Invalid token: {str(e)}'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'detail': f'Token verification failed: {str(e)}'}, status=status.HTTP_401_UNAUTHORIZED)

        email = idinfo.get('email')
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')
        google_uid = idinfo.get('sub')  # Google's unique user ID

        if not email:
            return Response({'detail': 'Google account must have an email.'}, status=status.HTTP_400_BAD_REQUEST)

        # Try to find an existing user by email
        try:
            user = User.objects.get(email=email)
            is_new_user = False
        except User.DoesNotExist:
            is_new_user = True
            # New user — user_type is mandatory
            if not user_type or user_type not in ('dealer', 'shopkeeper'):
                return Response(
                    {'detail': 'user_type is required for new accounts. Choose "dealer" or "shopkeeper".'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate a unique username from email
            base_username = email.split('@')[0].replace('.', '_').replace('+', '_')
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            # Split name
            name_parts = name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                user_type=user_type,
                is_verified=True,  # Google-verified emails are pre-verified
            )
            user.set_unusable_password()  # Google users don't have a local password
            user.save()

            # Auto-create business profile
            if user_type == 'dealer':
                from dealers.models import Dealer
                Dealer.objects.create(
                    user=user,
                    business_name=f"{first_name}'s Business" if first_name else f"{username}'s Business",
                    business_license=f"LICENSE-{user.id}-{username[:5]}",
                    business_category="General"
                )
            elif user_type == 'shopkeeper':
                from shopkeepers.models import Shopkeeper
                Shopkeeper.objects.create(
                    user=user,
                    shop_name=f"{first_name}'s Shop" if first_name else f"{username}'s Shop",
                    business_type="Retail"
                )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'is_new_user': is_new_user,
            'message': 'Google login successful'
        }, status=status.HTTP_200_OK)
