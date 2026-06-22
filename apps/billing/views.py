from rest_framework import mixins, viewsets
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.accounts.permissions import (
    IsCustomerSelf,
    IsFinanceStaff,
    IsInvoiceReader,
    OutletManagerReadOnly,
    outlet_location_ids,
)

from .models import CreditNote, Invoice, InvoiceLine
from .serializers import CreditNoteSerializer, InvoiceLineSerializer, InvoiceSerializer


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    Rule 7: cashier has NO access to finance/billing endpoints.
    Outlet managers can read invoices for their locations (read-only via OutletManagerReadOnly).
    Customers can read their own invoices.
    Writes (create, update) require manager/superuser (IsFinanceStaff).
    """
    serializer_class = InvoiceSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsInvoiceReader(), IsCustomerSelf(), OutletManagerReadOnly()]
        return [IsFinanceStaff()]

    def get_queryset(self):
        user = self.request.user
        qs = Invoice.objects.select_related('order', 'customer').prefetch_related('lines').order_by('-issued_at')
        if user.role == Role.CUSTOMER:
            qs = qs.filter(customer_id=getattr(user, 'customer_id', None))
        loc_ids = outlet_location_ids(user)
        if loc_ids is not None:
            qs = qs.filter(order__fulfilled_location__in=loc_ids)
        return qs

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'Invoices are immutable. Issue a CreditNote to reverse.'},
            status=405,
        )


class InvoiceLineViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    No update/delete — lines are immutable once created.
    Outlet managers can read lines for invoices within their locations.
    """
    serializer_class = InvoiceLineSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsSalesOrCustomer(), OutletManagerReadOnly()]
        return [IsFinanceStaff()]

    def get_queryset(self):
        qs = InvoiceLine.objects.select_related('invoice', 'product', 'price').order_by('id')
        invoice_id = self.request.query_params.get('invoice')
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)
        loc_ids = outlet_location_ids(self.request.user)
        if loc_ids is not None:
            qs = qs.filter(invoice__order__fulfilled_location__in=loc_ids)
        return qs


class CreditNoteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    CreditNotes are immutable once issued — no update or delete.
    Rule 7: cashier has NO access.
    Outlet managers can read credit notes for their locations.
    """
    serializer_class = CreditNoteSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsInvoiceReader(), OutletManagerReadOnly()]
        return [IsFinanceStaff()]

    def get_queryset(self):
        qs = CreditNote.objects.select_related('invoice', 'issued_by').order_by('-created_at')
        invoice_id = self.request.query_params.get('invoice')
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)
        loc_ids = outlet_location_ids(self.request.user)
        if loc_ids is not None:
            qs = qs.filter(invoice__order__fulfilled_location__in=loc_ids)
        return qs
