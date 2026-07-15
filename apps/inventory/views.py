from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import (
    IsInventoryStaff,
    OutletManagerReadOnly,
    outlet_location_ids,
)

from django.conf import settings as django_settings

from .models import StockMovement, StockTransfer
from .queries import current_stock, stock_matrix
from .serializers import StockMovementSerializer, StockTransferSerializer


class StockMovementViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Append-only ledger. Update and delete are structurally blocked.
    Outlet managers see movements at their assigned locations (read-only).
    """
    serializer_class = StockMovementSerializer
    permission_classes = [IsInventoryStaff, OutletManagerReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        qs = StockMovement.objects.select_related('product', 'location', 'lot', 'user').order_by('created_at')
        product_id = self.request.query_params.get('product')
        location_id = self.request.query_params.get('location')
        if product_id:
            qs = qs.filter(product_id=product_id)
        if location_id:
            qs = qs.filter(location_id=location_id)
        loc_ids = outlet_location_ids(self.request.user)
        if loc_ids is not None:
            qs = qs.filter(location__in=loc_ids)
        return qs


class StockTransferViewSet(
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Transfer headers are immutable once created — status transitions only via
    the confirm-receipt action. PUT/PATCH/DELETE are intentionally excluded.
    Outlet managers see transfers where their location appears on either end (read-only).
    """
    serializer_class = StockTransferSerializer
    permission_classes = [IsInventoryStaff, OutletManagerReadOnly]

    def get_queryset(self):
        qs = StockTransfer.objects.select_related(
            'from_location', 'to_location', 'received_by'
        ).order_by('-dispatched_at')
        loc_ids = outlet_location_ids(self.request.user)
        if loc_ids is not None:
            qs = qs.filter(
                Q(from_location__in=loc_ids) | Q(to_location__in=loc_ids)
            )
        return qs

    @action(detail=True, methods=['post'], url_path='confirm-receipt')
    def confirm_receipt(self, request, pk=None):
        transfer = self.get_object()
        try:
            transfer.confirm_receipt(user=request.user)
        except RuntimeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StockTransferSerializer(transfer).data)


class StockQueryView(viewsets.ViewSet):
    """
    GET /api/stock/?product=<id>&location=<id>
    Outlet managers may only query locations in their assigned set.
    Returns a single stock dict, not a list — pagination is not applicable.
    """
    permission_classes = [IsInventoryStaff, OutletManagerReadOnly]
    pagination_class = None  # single-row response, not a queryset list

    def list(self, request):
        product_id = request.query_params.get('product')
        location_id = request.query_params.get('location')
        if not product_id or not location_id:
            return Response(
                {'detail': 'Both product and location query params are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            product_id = int(product_id)
            location_id = int(location_id)
        except ValueError:
            return Response({'detail': 'product and location must be integers.'}, status=status.HTTP_400_BAD_REQUEST)

        loc_ids = outlet_location_ids(request.user)
        if loc_ids is not None and location_id not in loc_ids:
            return Response(
                {'detail': 'Location is not in your assigned outlets.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        result = current_stock(product_id, location_id)
        return Response({'product': product_id, 'location': location_id, **result})

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """
        GET /api/stock/summary/?location=<id>

        Stock on hand for every (product, location) pair in one aggregate, so the
        admin grid does not need N×M single-pair calls. Each row is flagged against
        LOW_STOCK_THRESHOLD_KG — the same threshold the low_stock_alert task uses.
        """
        loc_ids = outlet_location_ids(request.user)

        location_id = request.query_params.get('location')
        if location_id:
            try:
                location_id = int(location_id)
            except ValueError:
                return Response({'detail': 'location must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
            if loc_ids is not None and location_id not in loc_ids:
                return Response(
                    {'detail': 'Location is not in your assigned outlets.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            loc_ids = [location_id]

        threshold = getattr(django_settings, 'LOW_STOCK_THRESHOLD_KG', 10)
        rows = stock_matrix(location_ids=loc_ids)
        for row in rows:
            row['low_stock'] = row['qty_kg'] < threshold

        return Response({'threshold_kg': threshold, 'results': rows})
