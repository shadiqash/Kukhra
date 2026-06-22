from django.core.management.base import BaseCommand

from apps.inventory.tasks import low_stock_alert


class Command(BaseCommand):
    help = 'Manually trigger the low_stock_alert Celery task.'

    def handle(self, *args, **options):
        result = low_stock_alert.apply_async()
        self.stdout.write(f'low_stock_alert dispatched — task_id={result.id}')
