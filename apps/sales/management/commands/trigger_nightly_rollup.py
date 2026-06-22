from django.core.management.base import BaseCommand, CommandError

from apps.sales.tasks import nightly_rollup


class Command(BaseCommand):
    help = 'Manually trigger the nightly_rollup Celery task.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='ISO date to roll up (YYYY-MM-DD). Defaults to yesterday.',
        )

    def handle(self, *args, **options):
        target_date = options['date']
        result = nightly_rollup.apply_async(kwargs={'target_date': target_date})
        date_label = target_date or 'yesterday'
        self.stdout.write(f'nightly_rollup dispatched for {date_label} — task_id={result.id}')
