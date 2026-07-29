from django.contrib.auth import get_user_model
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .audit import audit
from .models import AuditLog, Role
from .permissions import IsManagerOrSuperuser
from .serializers import (
    ChangePasswordSerializer,
    SetPasswordSerializer,
    UserCreateSerializer,
    UserSerializer,
)


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'created_at', 'actor', 'action', 'model_name', 'object_id', 'diff']

User = get_user_model()


def revoke_outstanding_tokens(user) -> None:
    """
    Blacklist every refresh token the user still holds. Called on deactivation
    and password change so a stolen or stale refresh token dies with the event
    instead of staying valid for up to REFRESH_TOKEN_LIFETIME days.
    """
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    permission_classes = [IsManagerOrSuperuser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        audit(self.request.user, 'create', user,
              diff={'username': user.username, 'role': user.role})

    def perform_update(self, serializer):
        old_role = serializer.instance.role
        user = serializer.save()
        diff = {'fields': sorted(serializer.validated_data.keys() - {'password'})}
        if user.role != old_role:
            diff['role'] = [old_role, user.role]
        audit(self.request.user, 'update', user, diff=diff)

    def destroy(self, request, *args, **kwargs):
        """
        DELETE deactivates rather than hard-deletes. Ledger rows (StockMovement,
        CashierSession, …) reference users with PROTECT, so hard deletes 500 on
        any account with history — and an account is itself part of the audit
        trail. The serializer-level superuser guard never runs on destroy, so
        the role check is enforced here (a manager must not be able to remove
        the superuser and become the highest-privileged account standing).
        """
        target = self.get_object()
        if target.role == Role.SUPERUSER and request.user.role != Role.SUPERUSER:
            raise PermissionDenied('Only a superuser may deactivate a superuser account.')
        if target.pk == request.user.pk:
            return Response(
                {'detail': 'You cannot deactivate your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if target.is_active:
            target.is_active = False
            target.save(update_fields=['is_active'])
            revoke_outstanding_tokens(target)
            audit(request.user, 'deactivate', target, diff={'is_active': [True, False]})
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=True, methods=['post'], url_path='set-password')
    def set_password(self, request, pk=None):
        """
        Manager/superuser resets a user's password (e.g. a locked-out cashier).
        Superuser targets require a superuser requester — same rule as edits.
        """
        target = self.get_object()
        if target.role == Role.SUPERUSER and request.user.role != Role.SUPERUSER:
            raise PermissionDenied('Only a superuser may reset a superuser password.')
        ser = SetPasswordSerializer(data=request.data, context={'user': target})
        ser.is_valid(raise_exception=True)
        target.set_password(ser.validated_data['password'])
        target.save(update_fields=['password'])
        revoke_outstanding_tokens(target)
        audit(request.user, 'password_reset', target)
        return Response({'detail': 'Password updated.'})

    @action(detail=False, methods=['post'], url_path='change-password',
            permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Any authenticated user rotates their own password, proving the current one."""
        ser = ChangePasswordSerializer(data=request.data, context={'user': request.user})
        ser.is_valid(raise_exception=True)
        if not request.user.check_password(ser.validated_data['current_password']):
            return Response(
                {'current_password': ['Current password is incorrect.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(ser.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        revoke_outstanding_tokens(request.user)
        audit(request.user, 'password_change', request.user)
        return Response({'detail': 'Password changed.'})


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Read-only audit trail — manager/superuser only."""
    queryset = AuditLog.objects.select_related('user').order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsManagerOrSuperuser]
