from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsWarehouseStaff

from .models import Lot
from .serializers import LotSerializer, LotTransitionSerializer


class LotViewSet(viewsets.ModelViewSet):
    queryset = Lot.objects.select_related('supplier', 'arrival_location').order_by('-created_at')
    serializer_class = LotSerializer
    permission_classes = [IsWarehouseStaff]

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        lot = self.get_object()
        ser = LotTransitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            lot.transition(ser.validated_data['status'])
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LotSerializer(lot).data)
