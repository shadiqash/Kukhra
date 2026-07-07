from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class EverfreshTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds role and username to the JWT payload so the frontend can gate routes without an extra API call."""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        token['assigned_locations'] = list(
            user.assigned_locations.values_list('id', flat=True)
        )
        return token


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'customer', 'assigned_locations',
            'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'customer', 'assigned_locations', 'password',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        # M2M fields must be set after the initial save.
        assigned_locations = validated_data.pop('assigned_locations', [])
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if assigned_locations:
            user.assigned_locations.set(assigned_locations)
        return user
