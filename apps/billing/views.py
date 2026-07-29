from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets

from apps.accounts.audit import audit
from apps.accounts.models import Role
from apps.accounts.permissions import (
    IsCreditNoteReader,
    IsCustomerSelf,
    IsFinanceStaff,
    IsInvoiceReader,
    OutletManagerReadOnly,
    outlet_location_ids,
)

from .models import CreditNote, Invoice, InvoiceLine, compute_line_vat, next_invoice_number
from .serializers import CreditNoteSerializer, InvoiceLineSerializer, InvoiceSerializer


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    Rule 7: cashier has NO access to finance/billing endpoints.
    Outlet managers can read invoices for their locations (read-only via OutletManagerReadOnly).
    Customers can read their own invoices.
    Creation requires manager/superuser (IsFinanceStaff).

    Issued invoices are immutable: no PUT/PATCH/DELETE. Corrections are reversing
    CreditNotes, never edits to history.
    """
    http_method_names = ['get', 'post', 'head', 'options']
    serializer_class = InvoiceSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsInvoiceReader(), IsCustomerSelf(), OutletManagerReadOnly()]
        return [IsFinanceStaff()]

    def get_queryset(self):
        user = self.request.user
        qs = Invoice.objects.select_related('order', 'customer').prefetch_related('lines').order_by('-issued_at')
        if user.role == Role.CUSTOMER:
            customer_id = getattr(user, 'customer_id', None)
            # Fall closed: without a linked customer, `customer_id=None` would match
            # every walk-in invoice (they all have customer NULL) instead of none.
            if not customer_id:
                return qs.none()
            qs = qs.filter(customer_id=customer_id)
        loc_ids = outlet_location_ids(user)
        if loc_ids is not None:
            qs = qs.filter(order__fulfilled_location__in=loc_ids)
        return qs

    def perform_create(self, serializer):
        """
        H4: number and timestamp come from the server. The sequence hands out
        the next number under a row lock, so concurrent invoices cannot collide
        and a client can neither choose nor backdate a tax document.
        """
        invoice = serializer.save(invoice_number=next_invoice_number(), issued_at=timezone.now())
        audit(self.request.user, 'create', invoice,
              diff={'invoice_number': invoice.invoice_number, 'order': invoice.order_id})


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
            # Rule 7: cashier has NO billing access. IsInvoiceReader excludes CASHIER.
            return [IsInvoiceReader(), OutletManagerReadOnly()]
        return [IsFinanceStaff()]

    def get_queryset(self):
        user = self.request.user
        qs = InvoiceLine.objects.select_related('invoice', 'product', 'price').order_by('id')
        if user.role == Role.CUSTOMER:
            customer_id = getattr(user, 'customer_id', None)
            # Fall closed: an unlinked customer must see nothing, not every
            # walk-in invoice's lines (their invoices have customer NULL).
            if not customer_id:
                return qs.none()
            qs = qs.filter(invoice__customer_id=customer_id)
        invoice_id = self.request.query_params.get('invoice')
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)
        loc_ids = outlet_location_ids(user)
        if loc_ids is not None:
            qs = qs.filter(invoice__order__fulfilled_location__in=loc_ids)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Snapshot the tax class from the product and compute VAT server-side, then
        roll the parent invoice's header totals up from its lines. Without the
        recompute, every invoice header stayed at zero no matter what lines it held.
        """
        product = serializer.validated_data['product']
        line_total = serializer.validated_data['line_total_paisa']
        tax_class = product.tax_class
        line = serializer.save(
            tax_class=tax_class,
            vat_paisa=compute_line_vat(line_total, tax_class),
        )
        line.invoice.recompute_totals()


class CreditNoteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    CreditNotes are immutable once issued — no update or delete.
    Rule 7: cashier has NO access. Customer has NO access (matrix: credit-notes
    are internal reversal records, not customer-facing documents).
    Outlet managers can read credit notes for their locations.
    """
    serializer_class = CreditNoteSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsCreditNoteReader(), OutletManagerReadOnly()]
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

    def perform_create(self, serializer):
        # The reversal document records who actually issued it, when — stamped
        # from the request, never accepted from the payload.
        note = serializer.save(issued_by=self.request.user, issued_at=timezone.now())
        audit(self.request.user, 'create', note,
              diff={'invoice': note.invoice_id, 'amount_paisa': note.amount_paisa})
