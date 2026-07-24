from rest_framework import viewsets

from apps.accounts.permissions import IsLotStaff

from .models import ProcessingRun
from .serializers import ProcessingRunSerializer


class ProcessingRunViewSet(viewsets.ModelViewSet):
    # Runs are historical production events: create and read only, never edited
    # or deleted — their StockMovements are already in the append-only ledger.
    http_method_names = ['get', 'post', 'head', 'options']
    queryset = ProcessingRun.objects.select_related('lot', 'operator').order_by('-run_at')
    serializer_class = ProcessingRunSerializer
    permission_classes = [IsLotStaff]

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user)
