from rest_framework import mixins, viewsets

from apps.accounts.permissions import (
    IsManagerOrSuperuser,
    IsPriceReader,
    OutletManagerReadOnly,
    ReadOnlyOrManager,
)

from .models import Price, Product
from .serializers import PriceSerializer, ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    """Outlet managers get read-only access to the product catalog."""
    queryset = Product.objects.all().order_by('id')
    serializer_class = ProductSerializer
    permission_classes = [ReadOnlyOrManager, OutletManagerReadOnly]


class PriceViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Price rows are append-only (model blocks update/delete).
    Outlet managers can read prices (needed for sales reports).
    Rule 7: warehouse (worker) is blocked — IsPriceReader allows cashier/outlet_mgr/manager/superuser.
    Matrix: cashier is read-only on prices — setting a price is a manager decision.
    """
    queryset = Price.objects.all().order_by('-valid_from', 'id')
    serializer_class = PriceSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsPriceReader(), OutletManagerReadOnly()]
        return [IsManagerOrSuperuser()]

    def get_queryset(self):
        qs = super().get_queryset()
        product_id = self.request.query_params.get('product')
        if product_id:
            qs = qs.filter(product_id=product_id)
        tier = self.request.query_params.get('tier')
        if tier:
            qs = qs.filter(tier=tier)
        active = self.request.query_params.get('active')
        if active in ('1', 'true', 'True'):
            qs = qs.filter(valid_to__isnull=True)
        return qs
