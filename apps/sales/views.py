from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.accounts.permissions import (
    IsCustomerSelf,
    IsSalesOrCustomer,
    IsSalesStaff,
    OutletManagerReadOnly,
    outlet_location_ids,
)

from .models import CashierSession, Order, OrderLine, Payment
from .serializers import (
    CashierSessionSerializer,
    CloseSessionSerializer,
    OrderLineSerializer,
    OrderSerializer,
    PaymentSerializer,
)


class CashierSessionViewSet(viewsets.ModelViewSet):
    """
    Cashiers see only their own sessions.
    Outlet managers see sessions at their assigned locations (read-only).
    Rule 7: warehouse/procurement blocked (IsSalesStaff).
    """
    serializer_class = CashierSessionSerializer
    permission_classes = [IsSalesStaff, OutletManagerReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = CashierSession.objects.select_related('counter', 'cashier').order_by('-opened_at')
        if user.role == Role.CASHIER:
            qs = qs.filter(cashier=user)
        loc_ids = outlet_location_ids(user)
        if loc_ids is not None:
            qs = qs.filter(counter__location__in=loc_ids)
        return qs

    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        session = self.get_object()
        ser = CloseSessionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            session.close(ser.validated_data['closing_counted_paisa'])
        except RuntimeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CashierSessionSerializer(session).data)


class OrderViewSet(viewsets.ModelViewSet):
    """
    Cashiers and managers can access all orders.
    Outlet managers see orders at their assigned locations (read-only).
    Customer-role users see only their own orders.
    Rule 7: warehouse/procurement blocked.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsSalesOrCustomer, IsCustomerSelf, OutletManagerReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.select_related(
            'customer', 'fulfilled_location', 'session'
        ).prefetch_related('lines', 'payments').order_by('-created_at')
        if user.role == Role.CUSTOMER:
            qs = qs.filter(customer_id=getattr(user, 'customer_id', None))
        loc_ids = outlet_location_ids(user)
        if loc_ids is not None:
            qs = qs.filter(fulfilled_location__in=loc_ids)
        return qs

    @action(detail=True, methods=['post'], url_path='fulfill')
    def fulfill(self, request, pk=None):
        order = self.get_object()
        try:
            order.fulfill(user=request.user)
        except RuntimeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data)


class OrderLineViewSet(viewsets.ModelViewSet):
    """
    Outlet managers see lines for orders at their locations (read-only).
    Rule 7: warehouse/procurement blocked (IsSalesStaff).
    """
    serializer_class = OrderLineSerializer
    permission_classes = [IsSalesStaff, OutletManagerReadOnly]

    def get_queryset(self):
        qs = OrderLine.objects.select_related('order', 'product', 'price').order_by('id')
        order_id = self.request.query_params.get('order')
        if order_id:
            qs = qs.filter(order_id=order_id)
        loc_ids = outlet_location_ids(self.request.user)
        if loc_ids is not None:
            qs = qs.filter(order__fulfilled_location__in=loc_ids)
        return qs


class PaymentViewSet(viewsets.ModelViewSet):
    """
    Outlet managers see payments for orders at their locations (read-only).
    Rule 7: warehouse (worker) gets zero access to money/price/sales endpoints.
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsSalesStaff, OutletManagerReadOnly]

    def get_queryset(self):
        qs = Payment.objects.select_related('order').order_by('-created_at')
        order_id = self.request.query_params.get('order')
        if order_id:
            qs = qs.filter(order_id=order_id)
        loc_ids = outlet_location_ids(self.request.user)
        if loc_ids is not None:
            qs = qs.filter(order__fulfilled_location__in=loc_ids)
        return qs
