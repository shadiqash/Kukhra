from django.core.management.base import BaseCommand

from apps.billing.tasks import cbms_sync


class Command(BaseCommand):
    help = 'Manually trigger the cbms_sync Celery task (stub — no real IRD call).'

    def handle(self, *args, **options):
        result = cbms_sync.apply_async()
        self.stdout.write(f'cbms_sync dispatched — task_id={result.id}')
