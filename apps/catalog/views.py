from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError

from apps.accounts.audit import audit
from apps.accounts.permissions import (
    IsManagerOrSuperuser,
    IsPriceReader,
    OutletManagerReadOnly,
    ReadOnlyOrManager,
)

from .models import Price, Product
from .serializers import PriceSerializer, ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    """
    Outlet managers get read-only access to the product catalog.
    Filters: ?barcode=<exact> (POS scanner lookup), ?search=<name substring>.
    """
    queryset = Product.objects.all().order_by('id')
    serializer_class = ProductSerializer
    permission_classes = [ReadOnlyOrManager, OutletManagerReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        barcode = self.request.query_params.get('barcode')
        if barcode:
            qs = qs.filter(barcode=barcode)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


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

    def perform_create(self, serializer):
        price = serializer.save()
        # Price changes move real money — always audited.
        audit(self.request.user, 'create', price, diff={
            'product': price.product_id,
            'tier': price.tier,
            'price_paisa': price.price_paisa,
            'valid_from': str(price.valid_from),
        })

    def get_queryset(self):
        qs = super().get_queryset()
        product_id = self.request.query_params.get('product')
        if product_id:
            try:
                qs = qs.filter(product_id=int(product_id))
            except ValueError:
                raise ValidationError({'product': 'Must be an integer.'})
        tier = self.request.query_params.get('tier')
        if tier:
            qs = qs.filter(tier=tier)
        active = self.request.query_params.get('active')
        if active in ('1', 'true', 'True'):
            qs = qs.filter(valid_to__isnull=True)
        return qs
