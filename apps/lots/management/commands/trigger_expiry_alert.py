from django.core.management.base import BaseCommand

from apps.lots.tasks import expiry_alert


class Command(BaseCommand):
    help = 'Manually trigger the expiry_alert Celery task.'

    def handle(self, *args, **options):
        result = expiry_alert.apply_async()
        self.stdout.write(f'expiry_alert dispatched — task_id={result.id}')
