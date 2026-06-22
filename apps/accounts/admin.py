from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('username', 'email', 'role', 'is_active', 'is_staff')
    list_filter   = ('role', 'is_active', 'is_staff')
    fieldsets     = BaseUserAdmin.fieldsets + (
        ('Role & Contact', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role & Contact', {'fields': ('role', 'phone')}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ('created_at', 'user', 'action', 'model_name', 'object_id')
    list_filter   = ('action', 'model_name')
    search_fields = ('user__username', 'model_name')
    readonly_fields = ('created_at', 'updated_at', 'user', 'action', 'model_name', 'object_id', 'diff')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
