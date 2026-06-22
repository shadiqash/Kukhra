from rest_framework import viewsets
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.permissions import IsProcurementStaff, ReadOnlyOrManager

from .models import Customer, Supplier
from .serializers import CustomerSerializer, SupplierSerializer


class _SupplierWritePermission(BasePermission):
    """Procurement and above can write; other staff can read."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            from apps.accounts.models import Role
            return request.user.role not in (Role.CUSTOMER,)
        return IsProcurementStaff().has_permission(request, view)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by('id')
    serializer_class = SupplierSerializer
    permission_classes = [_SupplierWritePermission]


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('id')
    serializer_class = CustomerSerializer
    permission_classes = [ReadOnlyOrManager]
