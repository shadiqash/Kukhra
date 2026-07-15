from datetime import date

from django.db import transaction
from django.db.models import BigIntegerField, Count, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.accounts.permissions import (
    IsCustomerSelf,
    IsFinanceStaff,
    IsReportReader,
    IsSalesOrCustomer,
    IsSalesStaff,
    OutletManagerReadOnly,
    outlet_location_ids,
)
from apps.payments.services import consume_intent

from .models import CashierSession, Order, OrderLine, OrderStatus, Payment, PaymentMethod
from .serializers import (
    CashierSessionSerializer,
    CheckoutSerializer,
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

    def perform_create(self, serializer):
        serializer.save(cashier=self.request.user, opened_at=timezone.now())

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

    @action(detail=False, methods=['get'], url_path='reconciliation',
            permission_classes=[IsReportReader])
    def reconciliation(self, request):
        """
        GET /sessions/reconciliation/

        Every shift with expected cash vs counted cash and the variance between them.
        This is the shrinkage number: cash that was rung up but is not in the drawer.

        expected = opening float + cash taken (cancelled orders excluded — they were
        never money in the till). variance = counted − expected; negative means short.
        Open shifts have no counted figure yet, so variance is null rather than a
        misleading zero.

        Subqueries, not annotated joins: summing orders and payments in one query
        would multiply rows across the two join paths and inflate both totals.
        """
        cash_taken = (
            Payment.objects
            .filter(order__session=OuterRef('pk'), method=PaymentMethod.CASH)
            .exclude(order__status=OrderStatus.CANCELLED)
            .values('order__session')
            .annotate(total=Sum('amount_paisa'))
            .values('total')
        )
        sales_total = (
            Order.objects
            .filter(session=OuterRef('pk'))
            .exclude(status=OrderStatus.CANCELLED)
            .values('session')
            .annotate(total=Sum('total_paisa'))
            .values('total')
        )
        sales_count = (
            Order.objects
            .filter(session=OuterRef('pk'))
            .exclude(status=OrderStatus.CANCELLED)
            .values('session')
            .annotate(n=Count('id'))
            .values('n')
        )

        sessions = self.get_queryset().annotate(
            cash_sales_paisa=Coalesce(Subquery(cash_taken), 0, output_field=BigIntegerField()),
            sales_total_paisa=Coalesce(Subquery(sales_total), 0, output_field=BigIntegerField()),
            sales_count=Coalesce(Subquery(sales_count), 0, output_field=BigIntegerField()),
        )

        # Bounded by default: without a range this would return every shift ever opened.
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        try:
            if date_from:
                sessions = sessions.filter(opened_at__date__gte=date.fromisoformat(date_from))
            if date_to:
                sessions = sessions.filter(opened_at__date__lte=date.fromisoformat(date_to))
        except ValueError:
            raise ValidationError({'detail': 'Dates must be ISO format (YYYY-MM-DD).'})

        rows = []
        for s in sessions:
            expected = s.opening_float_paisa + s.cash_sales_paisa
            counted = s.closing_counted_paisa
            rows.append({
                'id': s.pk,
                'cashier': s.cashier.username,
                'counter': s.counter.name,
                'location': s.counter.location_id,
                'location_name': s.counter.location.name,
                'opened_at': s.opened_at,
                'closed_at': s.closed_at,
                'is_open': s.closed_at is None,
                'opening_float_paisa': s.opening_float_paisa,
                'cash_sales_paisa': s.cash_sales_paisa,
                'expected_cash_paisa': expected,
                'closing_counted_paisa': counted,
                # Null while the shift is still open — there is nothing to compare yet.
                'variance_paisa': None if counted is None else counted - expected,
                'sales_count': s.sales_count,
                'sales_total_paisa': s.sales_total_paisa,
            })
        return Response({'results': rows})

    @action(detail=True, methods=['get'], url_path='summary')
    def summary(self, request, pk=None):
        session = self.get_object()
        # Cancelled orders never put money in the drawer, so they must not appear
        # in the Z-report totals or inflate the expected cash.
        live_orders = session.orders.exclude(status=OrderStatus.CANCELLED)
        agg = live_orders.aggregate(
            sales_count=Count('id'),
            sales_total=Sum('total_paisa'),
        )
        payment_rows = list(
            Payment.objects
            .filter(order__session=session)
            .exclude(order__status=OrderStatus.CANCELLED)
            .values('method')
            .annotate(total=Sum('amount_paisa'), count=Count('id'))
        )
        cash_sales = next((r['total'] for r in payment_rows if r['method'] == 'cash'), 0) or 0
        variance = (session.closing_counted_paisa or 0) - (session.opening_float_paisa + cash_sales)
        payload = {
            # The float is cash the cashier was physically handed — no point hiding it.
            'opening_float_paisa': session.opening_float_paisa,
            'sales_count': agg['sales_count'] or 0,
            'sales_total_paisa': agg['sales_total'] or 0,
            'payment_breakdown': payment_rows,
            'opened_at': session.opened_at,
            'closed_at': session.closed_at,
        }

        # Rule 7. The drawer audit is a manager's number, not the cashier's: handing a
        # cashier their own variance tells them exactly how much they could take without
        # it showing. The count itself is already blind — close() takes the counted figure
        # before this endpoint reveals anything, and a session cannot be closed twice.
        if request.user.role != Role.CASHIER:
            payload.update({
                'closing_counted_paisa': session.closing_counted_paisa,
                'cash_sales_paisa': cash_sales,
                'expected_cash_paisa': session.opening_float_paisa + cash_sales,
                'variance_paisa': variance,
            })
        return Response(payload)


class OrderViewSet(viewsets.ModelViewSet):
    """
    Cashiers and managers can access all orders.
    Outlet managers see orders at their assigned locations (read-only).
    Customer-role users see only their own orders.
    Rule 7: warehouse/procurement blocked.

    Orders are financial records: once created they are immutable. PUT/PATCH/DELETE
    are structurally absent — a mis-rung sale is undone via the manager-only
    `cancel` action, which posts reversing ledger rows rather than editing history.
    """
    http_method_names = ['get', 'post', 'head', 'options']
    serializer_class = OrderSerializer
    permission_classes = [IsSalesOrCustomer, IsCustomerSelf, OutletManagerReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.select_related(
            'customer', 'fulfilled_location', 'session'
        ).prefetch_related('lines', 'payments').order_by('-created_at')
        if user.role == Role.CUSTOMER:
            customer_id = getattr(user, 'customer_id', None)
            # Fall closed: without a linked customer, `customer_id=None` would match
            # every walk-in order (they all have customer NULL) instead of none.
            if not customer_id:
                return qs.none()
            qs = qs.filter(customer_id=customer_id)
        loc_ids = outlet_location_ids(user)
        if loc_ids is not None:
            qs = qs.filter(fulfilled_location__in=loc_ids)
        return self._apply_filters(qs)

    def _apply_filters(self, qs):
        """
        Report filters: outlet, status, and an inclusive created_at date range.
        Outlet-manager scoping in get_queryset is applied first and always wins —
        these only ever narrow the set further.

        Malformed values raise DRF ValidationError (400) rather than reaching the
        ORM, where a bad date would surface as a 500.
        """
        params = self.request.query_params

        location_id = params.get('fulfilled_location')
        if location_id:
            try:
                qs = qs.filter(fulfilled_location_id=int(location_id))
            except ValueError:
                raise ValidationError({'fulfilled_location': 'Must be an integer.'})

        order_status = params.get('status')
        if order_status:
            if order_status not in OrderStatus.values:
                raise ValidationError({'status': f'Must be one of {OrderStatus.values}.'})
            qs = qs.filter(status=order_status)

        for param, lookup in (('date_from', 'created_at__date__gte'),
                              ('date_to', 'created_at__date__lte')):
            raw = params.get(param)
            if not raw:
                continue
            try:
                parsed = date.fromisoformat(raw)
            except ValueError:
                raise ValidationError({param: 'Must be an ISO date (YYYY-MM-DD).'})
            qs = qs.filter(**{lookup: parsed})

        return qs

    @action(detail=False, methods=['get'], url_path='summary',
            permission_classes=[IsReportReader])
    def summary(self, request):
        """
        GET /orders/summary/?date_from=&date_to=&fulfilled_location=

        Aggregate over the whole filtered set — a dashboard KPI must never be the
        sum of one page. Cancelled orders are excluded from revenue: they are kept
        in the ledger for audit but were never money in the till.

        Rule 7: this is a finance report. It carries its own permission rather than
        inheriting the viewset's sales-write set, which admits cashiers.
        """
        qs = self.get_queryset().exclude(status=OrderStatus.CANCELLED)
        agg = qs.aggregate(order_count=Count('id'), gross_paisa=Sum('total_paisa'))
        return Response({
            'order_count': agg['order_count'] or 0,
            'gross_paisa': agg['gross_paisa'] or 0,   # integer paisa — never float
        })

    @action(detail=True, methods=['post'], url_path='fulfill')
    def fulfill(self, request, pk=None):
        order = self.get_object()
        try:
            order.fulfill(user=request.user)
        except RuntimeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='cancel',
            permission_classes=[IsFinanceStaff])
    def cancel(self, request, pk=None):
        """
        POST /orders/{id}/cancel/  — manager/superuser only.

        Voids the order and reverses its sale movements. Rule 7: a cashier must not
        be able to erase their own takings, so this carries IsFinanceStaff (manager/
        superuser) rather than the viewset's sales-write set. Outlet managers are
        read-only and cannot cancel either.
        """
        order = self.get_object()
        try:
            order.cancel(user=request.user)
        except RuntimeError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data)

    def create(self, request, *args, **kwargs):
        """
        POST /orders/ normally just creates a bare pending Order (legacy /
        step-by-step flow). If the payload also carries `lines`/`payments`
        (the POS one-shot checkout), create the order, its lines, its
        payments, and fulfill it — all in a single DB transaction — so a
        mid-sequence failure never leaves a partial order behind.
        """
        if isinstance(request.data, dict) and 'lines' in request.data:
            try:
                return self._checkout(request)
            except (RuntimeError, ValueError) as exc:
                # RuntimeError: insufficient stock. ValueError: a payment intent that
                # was spent, unverified, or for the wrong amount. Both roll the
                # transaction back and neither is a server fault.
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def _checkout(self, request):
        serializer = CheckoutSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order = Order.objects.create(
            customer=data.get('customer'),
            fulfilled_location=data['fulfilled_location'],
            session=data.get('session'),
            source=data['source'],
            total_paisa=data['total_paisa'],
        )
        OrderLine.objects.bulk_create([
            OrderLine(order=order, **line) for line in data['lines']
        ])

        # Spend each gateway payment exactly once. consume_intent locks the intent row
        # and flips it to CONSUMED, so two tills cannot settle two baskets against the
        # same scanned QR — the second finds it already spent and the whole checkout
        # rolls back. Serializer validation already proved it is verified and correct.
        for payment in data['payments']:
            intent = payment.get('intent')
            if intent is not None:
                consume_intent(intent, amount_paisa=payment['amount_paisa'])

        Payment.objects.bulk_create([
            Payment(order=order, **payment) for payment in data['payments']
        ])
        # Propagates RuntimeError('Insufficient stock …') on shortfall, which
        # rolls back the whole transaction — order/lines/payments included.
        order.fulfill(user=request.user)

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderLineViewSet(viewsets.ModelViewSet):
    """
    Outlet managers see lines for orders at their locations (read-only).
    Rule 7: warehouse/procurement blocked (IsSalesStaff).
    Immutable once written — PUT/PATCH/DELETE are structurally absent.
    """
    http_method_names = ['get', 'post', 'head', 'options']
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
    Immutable once recorded — a taken payment cannot be edited or deleted away.
    """
    http_method_names = ['get', 'post', 'head', 'options']
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

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Spend the intent as the payment is written, in one transaction. The
        serializer has already proved the intent is VERIFIED and for the right
        amount; consume_intent locks it and flips it to CONSUMED so the same scanned
        QR can never settle a second order. Without this the step-by-step path left
        the intent reusable and relied on a raw IntegrityError (500) to stop reuse.
        """
        intent = serializer.validated_data.get('intent')
        if intent is not None:
            consume_intent(intent, amount_paisa=serializer.validated_data['amount_paisa'])
        serializer.save()
