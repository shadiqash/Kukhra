from django.contrib.auth import get_user_model
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AuditLog
from .permissions import IsManagerOrSuperuser
from .serializers import UserCreateSerializer, UserSerializer


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'created_at', 'actor', 'action', 'model_name', 'object_id', 'diff']

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    permission_classes = [IsManagerOrSuperuser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        return Response(UserSerializer(request.user).data)


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Read-only audit trail — superuser only."""
    queryset = AuditLog.objects.select_related('user').order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsManagerOrSuperuser]
