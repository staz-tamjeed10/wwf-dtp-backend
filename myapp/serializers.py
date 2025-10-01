from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password


class UserSerializer(serializers.ModelSerializer):
    is_superuser = serializers.BooleanField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_superuser', 'is_staff']


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    # Change these to ListField to properly handle arrays
    leather_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    animal_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    certifications = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )

    class Meta:
        model = Profile
        fields = '__all__'

    def to_internal_value(self, data):
        # Convert string fields to lists if needed
        for field in ['leather_types', 'animal_types', 'certifications']:
            if field in data and isinstance(data[field], str):
                data[field] = [x.strip() for x in data[field].split(',') if x.strip()]
        return super().to_internal_value(data)


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    full_name = serializers.CharField(required=True)
    contact_person = serializers.CharField(required=True)
    registered_since = serializers.DateField(required=True)
    contact_no = serializers.CharField(required=True)
    role = serializers.CharField(required=True)
    business_type = serializers.CharField(required=False, allow_blank=True)
    operation_type = serializers.CharField(required=False, allow_blank=True)
    leather_types = serializers.CharField(required=False, allow_blank=True)
    animal_types = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=True)
    location = serializers.CharField(required=False, allow_blank=True)
    brand = serializers.CharField(required=False, allow_blank=True)
    certifications = serializers.CharField(required=False, allow_blank=True)
    terms = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2', 'full_name', 'contact_person',
            'registered_since', 'contact_no', 'role', 'business_type', 'operation_type',
            'leather_types', 'animal_types', 'city', 'location',
            'brand', 'certifications', 'terms'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        # Create user first
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            is_active=False
        )
        user.set_password(validated_data['password'])
        user.save()

        # Profile data to save
        profile_data = {
            'full_name': validated_data['full_name'],
            'contact_person': validated_data['contact_person'],
            'registered_since': validated_data['registered_since'],
            'contact_no': validated_data['contact_no'],
            'role': validated_data['role'],
            'business_type': validated_data.get('business_type', ''),
            'operation_type': validated_data.get('operation_type', ''),
            'leather_types': validated_data.get('leather_types', ''),
            'animal_types': validated_data.get('animal_types', ''),
            'city': validated_data['city'],
            'location': validated_data.get('location', ''),
            'brand': validated_data.get('brand', ''),
            'certifications': validated_data.get('certifications', '')
        }

        # Get or create profile
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults=profile_data
        )

        # If profile already existed, update it
        if not created:
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    new_password2 = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {"new_password": "Password fields didn't match."})
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)
    new_password2 = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {"new_password": "Password fields didn't match."})
        return attrs
