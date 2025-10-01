from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.db import IntegrityError
from django.contrib.auth.models import User
from .models import Profile
from .serializers import *
import uuid
from django.db import transaction
from rest_framework.generics import GenericAPIView


class RegisterAPI(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        print("Incoming registration data:", request.data)

        if User.objects.filter(email=request.data.get('email')).exists():
            return Response(
                {'email': ['This email is already registered. Please login instead.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = serializer.save()
            profile = self.create_user_profile(user, request.data)
            self.send_verification_email(request, user, profile.verification_token)

            return Response(
                {'message': 'Verification email sent. Please check your inbox.'},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            print("Registration error:", str(e))
            return Response(
                {'error': 'An error occurred during registration'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create_user_profile(self, user, data):
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'contact_no': data.get('contact_no', ''),
                'role': data.get('role', 'visitor'),
                'business_type': data.get('business_type', ''),
                'leather_types': data.get('leather_types', ''),
                'animal_types': data.get('animal_types', ''),
                'city': data.get('city', ''),
                'brand': data.get('brand', ''),
                'location': data.get('location', ''),
                'operation_type': data.get('operation_type', ''),
                'certifications': data.get('certifications', ''),
            }
        )
        profile.verification_token = str(uuid.uuid4())
        profile.token_created_at = timezone.now()
        profile.save()
        print(f"Generated token: {profile.verification_token}")  # Debug
        return profile

    def send_verification_email(self, request, user, token):
        try:
            current_site = get_current_site(request)
            mail_subject = 'Verify your email address'
            message = render_to_string('email_verification.html', {
                'user': user,
                'domain': current_site.domain,
                'token': token,
                'protocol': 'https' if request.is_secure() else 'http',
            })
            send_mail(
                mail_subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Email sending failed: {str(e)}")


class VerifyEmailAPI(GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            if not token or token.lower() == 'none':
                raise ValueError("Invalid token")

            profile = Profile.objects.select_related('user').get(
                verification_token=token,
                token_created_at__gte=timezone.now() - timezone.timedelta(days=1)
            )

            if not profile.email_verified:
                profile.email_verified = True
                profile.user.is_active = True
                profile.user.save()
                profile.save()

                auth_token, created = Token.objects.get_or_create(user=profile.user)

                return Response({
                    'message': 'Email successfully verified!',
                    'token': auth_token.key,
                    'user_id': profile.user.id,
                    'email': profile.user.email
                }, status=status.HTTP_200_OK)

            return Response(
                {'message': 'Email already verified'},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            print(f"Verification failed: {str(e)}")
            return Response(
                {'error': 'Invalid or expired verification link'},
                status=status.HTTP_400_BAD_REQUEST
            )

@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=user.username, password=password)
        if user is not None:
            if not user.is_active:
                return Response({'error': 'Account not activated. Please verify your email.'},
                                status=status.HTTP_400_BAD_REQUEST)

            # Create or get token
            token, created = Token.objects.get_or_create(user=user)

            # Login the user
            login(request, user)

            # Get profile data
            profile = Profile.objects.get(user=user)
            profile_serializer = ProfileSerializer(profile)

            return Response({
                'token': token.key,
                'user_id': user.pk,
                'email': user.email,
                'username': user.username,
                'profile': profile_serializer.data,
                'role': profile.role,
                'is_superuser': user.is_superuser,  # Add this
                'is_staff': user.is_staff,          # Add this
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    # Delete the token
    request.user.auth_token.delete()
    logout(request)
    return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_api(request):
    profile = Profile.objects.get(user=request.user)
    serializer = ProfileSerializer(profile)
    
    # Include superuser information in the response
    response_data = serializer.data
    response_data['is_superuser'] = request.user.is_superuser
    response_data['is_staff'] = request.user.is_staff
    response_data['user'] = {
        'is_superuser': request.user.is_superuser,
        'is_staff': request.user.is_staff,
        'username': request.user.username,
        'email': request.user.email
    }
    
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile_api(request):
    try:
        user = request.user
        profile = Profile.objects.get(user=user)
        data = request.data.copy()

        # Debug logging
        print("Raw incoming data:", data)

        # Handle array fields
        array_fields = ['leather_types', 'animal_types', 'certifications']
        for field in array_fields:
            if field in data:
                if isinstance(data[field], str):
                    # Convert string to list
                    data[field] = [x.strip() for x in data[field].split(',') if x.strip()]
                elif isinstance(data[field], list):
                    # If it's a list of individual characters, reconstruct
                    if data[field] and isinstance(data[field][0], str) and len(data[field][0]) == 1:
                        reconstructed = ''.join(data[field])
                        data[field] = [x.strip() for x in reconstructed.split(',') if x.strip()]

        serializer = ProfileSerializer(profile, data=data, partial=True)
        user_serializer = UserSerializer(user, data=data.get('user', {}), partial=True)

        if serializer.is_valid() and user_serializer.is_valid():
            serializer.save()
            user_serializer.save()
            return Response(serializer.data)

        errors = {}
        if user_serializer.errors:
            errors['user'] = user_serializer.errors
        if serializer.errors:
            errors['profile'] = serializer.errors

        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    except Profile.DoesNotExist:
        return Response(
            {"error": "Profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print("Server error:", str(e))
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    serializer = PasswordChangeSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(old_password):
            return Response({'old_password': 'Wrong password.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        # Update session auth hash
        update_session_auth_hash(request, user)

        return Response({'message': 'Password successfully changed.'}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_api(request):
    serializer = PasswordResetSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate token and send email (similar to your existing view)
        # ...
        return Response({'message': 'Password reset email sent.'}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm_api(request, uidb64, token):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if serializer.is_valid():
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None:
            new_password = serializer.validated_data['new_password']
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Password has been reset.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid reset link.'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# @api_view(['GET'])
# @permission_classes([AllowAny])
# def activate_account_api(request, uidb64, token):
#     try:
#         uid = force_str(urlsafe_base64_decode(uidb64))
#         user = User.objects.get(pk=uid)
#     except (TypeError, ValueError, OverflowError, User.DoesNotExist):
#         user = None
#
#     profile = Profile.objects.filter(user=user, verification_token=token).first()
#     if profile and not profile.email_verified:
#         profile.email_verified = True
#         user.is_active = True
#         user.save()
#         profile.save()
#
#         # Create token for the user
#         token, created = Token.objects.get_or_create(user=user)
#
#         return Response({'message': 'Account activated successfully. You can now login.'},
#                         status=status.HTTP_200_OK)
#     else:
#         return Response({'error': 'Activation link is invalid!'},
#                         status=status.HTTP_400_BAD_REQUEST)
