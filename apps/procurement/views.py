from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsProcurementStaff
from apps.catalog.models import Product
from apps.lots.models import Lot

from .models import GoodsReceived, PurchaseOrder, PurchaseOrderStatus
from .serializers import (
    GoodsReceiveLineSerializer,
    GoodsReceivedSerializer,
    PurchaseOrderSerializer,
)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('supplier').order_by('-created_at')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsProcurementStaff]

    def _move(self, request, pk, new_status):
        po = self.get_object()
        try:
            po.transition(new_status)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=['post'], url_path='send')
    def send(self, request, pk=None):
        """Draft → Sent. The PO has gone to the supplier."""
        return self._move(request, pk, PurchaseOrderStatus.SENT)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """Draft or Sent → Cancelled. A received PO can no longer be cancelled."""
        return self._move(request, pk, PurchaseOrderStatus.CANCELLED)


class GoodsReceivedViewSet(viewsets.ModelViewSet):
    """
    A goods receipt is the source document for production movements in an
    append-only ledger, so it is immutable once written: PUT/PATCH/DELETE are
    structurally excluded. Editing a receipt's location after it created the
    movements would let the document contradict the ledger it produced; deleting
    it would orphan rows that can never be removed. Corrections are new documents.
    """
    http_method_names = ['get', 'post', 'head', 'options']
    queryset = GoodsReceived.objects.select_related(
        'purchase_order', 'location', 'received_by', 'lot'
    ).order_by('-received_at')
    serializer_class = GoodsReceivedSerializer
    permission_classes = [IsProcurementStaff]

    @action(detail=True, methods=['post'], url_path='receive')
    def receive(self, request, pk=None):
        """
        POST /api/procurement/goods-received/{id}/receive/
        Body: {"lines": [{"product": <id>, "qty_kg": ..., "qty_pieces": ..., "lot": <id|null>}]}
        Creates StockMovement(type=production) rows and marks the PO received.
        """
        gr = self.get_object()
        lines_data = request.data.get('lines', [])
        line_ser = GoodsReceiveLineSerializer(data=lines_data, many=True)
        line_ser.is_valid(raise_exception=True)

        lines = []
        for item in line_ser.validated_data:
            try:
                product = Product.objects.get(pk=item['product'])
            except Product.DoesNotExist:
                return Response(
                    {'detail': f"Product {item['product']} not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            lot = None
            if item.get('lot'):
                try:
                    lot = Lot.objects.get(pk=item['lot'])
                except Lot.DoesNotExist:
                    return Response(
                        {'detail': f"Lot {item['lot']} not found."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            lines.append({
                'product':    product,
                'qty_kg':     item['qty_kg'],
                'qty_pieces': item['qty_pieces'],
                'lot':        lot,
            })

        try:
            gr.receive(user=request.user, lines=lines)
        except (ValueError, RuntimeError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(GoodsReceivedSerializer(gr).data, status=status.HTTP_200_OK)
