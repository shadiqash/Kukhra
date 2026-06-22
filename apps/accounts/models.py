from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import BaseModel


class Role(models.TextChoices):
    SUPERUSER      = 'superuser',      'Superuser'
    MANAGER        = 'manager',        'Manager'
    OUTLET_MANAGER = 'outlet_manager', 'Outlet Manager'
    CASHIER        = 'cashier',        'Cashier'
    WAREHOUSE      = 'warehouse',      'Warehouse Staff'
    PROCUREMENT    = 'procurement',    'Procurement'
    CUSTOMER       = 'customer',       'Customer'


class User(AbstractUser):
    """
    Custom user model — always referenced via settings.AUTH_USER_MODEL.
    This is the first migration for accounts; never squash it.
    """
    role     = models.CharField(max_length=20, choices=Role.choices, default=Role.CASHIER)
    phone    = models.CharField(max_length=20, blank=True)
    # Phase 1 stub: links a customer-role user to their partners.Customer record.
    # Phase 2 will add full customer auth flow and mobile app.
    customer = models.OneToOneField(
        'partners.Customer',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='user',
    )
    # Outlet managers are scoped to one or more locations. Ignored for all other roles.
    assigned_locations = models.ManyToManyField(
        'locations.Location',
        blank=True,
        related_name='outlet_managers',
    )

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class AuditLog(BaseModel):
    """Immutable record of every significant state change. Never edit rows here."""
    user       = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='audit_logs')
    action     = models.CharField(max_length=50)           # e.g. 'create', 'update', 'transition'
    model_name = models.CharField(max_length=100)
    object_id  = models.PositiveBigIntegerField(null=True)
    diff       = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']
        db_table = 'accounts_audit_log'

    def delete(self, *args, **kwargs):
        raise RuntimeError('AuditLog rows are immutable and must never be deleted.')

    def __str__(self):
        return f'{self.action} {self.model_name}#{self.object_id} by {self.user_id}'
