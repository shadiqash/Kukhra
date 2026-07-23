from rest_framework import viewsets

from apps.accounts.models import Role
from apps.accounts.permissions import OutletManagerReadOnly, ReadOnlyOrManager, outlet_location_ids

from .models import Counter, Location
from .serializers import CounterSerializer, LocationSerializer


class LocationViewSet(viewsets.ModelViewSet):
    """Outlet managers see only their assigned locations (read-only)."""
    serializer_class = LocationSerializer
    permission_classes = [ReadOnlyOrManager, OutletManagerReadOnly]

    def get_queryset(self):
        qs = Location.objects.all().order_by('id')
        loc_ids = outlet_location_ids(self.request.user)
        if loc_ids is not None:
            qs = qs.filter(pk__in=loc_ids)
        return qs


class CounterViewSet(viewsets.ModelViewSet):
    """
    Outlet managers see only counters at their assigned locations (read-only).
    Cashiers see only counters at their assigned locations — the POS binds the
    till to the first counter it gets back, so an unscoped list would point
    every outlet's till at the same counter.
    """
    serializer_class = CounterSerializer
    permission_classes = [ReadOnlyOrManager, OutletManagerReadOnly]

    def get_queryset(self):
        qs = Counter.objects.all().order_by('id')
        user = self.request.user
        if user.is_authenticated and user.role == Role.CASHIER:
            return qs.filter(location__in=user.assigned_locations.all())
        loc_ids = outlet_location_ids(user)
        if loc_ids is not None:
            qs = qs.filter(location__in=loc_ids)
        return qs
