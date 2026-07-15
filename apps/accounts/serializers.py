from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Role

User = get_user_model()


class SuperuserRoleGuardMixin:
    """
    Only a superuser may mint or touch a superuser account. Without this, a manager
    — who has full write on /users/ — could create a superuser, or PATCH their own
    role to superuser, and escalate past every role check in the system.
    """
    def _requester_role(self):
        request = self.context.get('request')
        return getattr(getattr(request, 'user', None), 'role', None)

    def validate_role(self, role):
        if role == Role.SUPERUSER and self._requester_role() != Role.SUPERUSER:
            raise serializers.ValidationError('Only a superuser may grant the superuser role.')
        return role

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Editing an existing superuser is itself a superuser-only act.
        if (
            self.instance is not None
            and getattr(self.instance, 'role', None) == Role.SUPERUSER
            and self._requester_role() != Role.SUPERUSER
        ):
            raise serializers.ValidationError('Only a superuser may modify a superuser account.')
        return attrs


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


class UserSerializer(SuperuserRoleGuardMixin, serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'customer', 'assigned_locations',
            'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']


class UserCreateSerializer(SuperuserRoleGuardMixin, serializers.ModelSerializer):
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
