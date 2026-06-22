from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """Abstract base for every table: surrogate PK + timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditMixin(models.Model):
    """Abstract mixin for user-tracked tables. Combine with BaseModel."""
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    class Meta:
        abstract = True
