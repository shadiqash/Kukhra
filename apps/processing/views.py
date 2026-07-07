from rest_framework import viewsets

from apps.accounts.permissions import IsWarehouseStaff

from .models import ProcessingRun
from .serializers import ProcessingRunSerializer


class ProcessingRunViewSet(viewsets.ModelViewSet):
    queryset = ProcessingRun.objects.select_related('lot', 'operator').order_by('-run_at')
    serializer_class = ProcessingRunSerializer
    permission_classes = [IsWarehouseStaff]

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user)
