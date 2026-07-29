"""
Write-side of the audit trail. AuditLog rows are immutable (the model blocks
update/delete); this helper is the one sanctioned way to add them.

Called inside the same transaction as the mutation it records, so an audited
change and its audit row commit or roll back together — an unauditable
mutation never half-lands.

Never put secrets in `diff` (passwords, tokens). Record that the event
happened and which fields moved, not sensitive values.
"""
from .models import AuditLog


def audit(user, action: str, instance=None, *, model_name: str | None = None,
          object_id=None, diff: dict | None = None) -> None:
    """
    Record `action` on `instance` by `user`.

    diff values must be JSON-serializable — stringify Decimals at the call site.
    """
    AuditLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        action=action,
        model_name=model_name or type(instance).__name__,
        object_id=object_id if object_id is not None else getattr(instance, 'pk', None),
        diff=diff or {},
    )
