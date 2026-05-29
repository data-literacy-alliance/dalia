"""
Management command to process scheduled account deletions.

This should be run periodically (e.g., daily via cron) to process confirmed deletion
requests that have passed their 30-day grace period.

Usage:
    python manage.py process_scheduled_deletions [--dry-run]

Options:
    --dry-run: Show what would be deleted without actually deleting

Cron example (runs daily at 2 AM):
    0 2 * * * cd /app && python manage.py process_scheduled_deletions >> /var/log/deletion_processing.log 2>&1
"""

from account_deletion.models import AccountDeletionRequest
from account_deletion.services import AccountDeletionService
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Process deletion requests that have passed their 30-day grace period'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--admin-user',
            type=str,
            help='Username of admin user to attribute deletions to (default: system)',
        )

    def handle(self, *args, **options):
        """Execute the command."""
        dry_run = options['dry_run']
        admin_username = options.get('admin_user')

        # Get admin user if specified
        admin_user = None
        if admin_username:
            try:
                admin_user = User.objects.get(username=admin_username)
                if not (admin_user.is_staff or admin_user.is_superuser):
                    self.stdout.write(
                        self.style.WARNING(f'User {admin_username} is not staff/superuser')
                    )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Admin user {admin_username} not found')
                )
                return

        self.stdout.write('Checking for scheduled deletions...')

        ready_requests = AccountDeletionRequest.objects.filter(
            status='confirmed',
            deletion_scheduled_at__lt=timezone.now()
        ).select_related('user')

        count = ready_requests.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No deletions scheduled for processing')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'Found {count} deletion request(s) ready for processing')
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE('\n--- DRY RUN MODE - No actual deletions will occur ---\n')
            )
            for req in ready_requests:
                self.stdout.write(
                    f'  Would delete: User #{req.user.id} ({req.user.username}) - '
                    f'Request #{req.id} scheduled for {req.deletion_scheduled_at}'
                )
                items = req.items.all()
                self.stdout.write(f'    - {items.count()} content items to process')
            return

        # Process deletions
        processed_count = 0
        error_count = 0

        for req in ready_requests:
            self.stdout.write(
                f'\nProcessing deletion request #{req.id} for user {req.user.username}...'
            )

            try:
                AccountDeletionService.process_deletion(
                    deletion_request=req,
                    admin_user=admin_user
                )
                processed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  Successfully processed request #{req.id}')
                )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  Error processing request #{req.id}: {e}')
                )

        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'Successfully processed: {processed_count}')
        )
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'Failed: {error_count}')
            )
        self.stdout.write('='*50)
