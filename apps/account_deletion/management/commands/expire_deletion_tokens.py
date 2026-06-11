"""
Management command to expire old deletion request tokens.

This should be run periodically (e.g., hourly via cron) to mark pending requests
with expired tokens as 'expired'.

Usage:
    python manage.py expire_deletion_tokens

Cron example (runs every hour):
    0 * * * * cd /app && python manage.py expire_deletion_tokens >> /var/log/deletion_expiry.log 2>&1
"""

from account_deletion.services import AccountDeletionService
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Expire deletion request tokens that have passed their 7-day validity period"

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write("Checking for expired deletion request tokens...")

        try:
            count = AccountDeletionService.expire_old_tokens()

            if count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully expired {count} deletion request token(s)")
                )
            else:
                self.stdout.write(self.style.SUCCESS("No expired tokens found"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error expiring tokens: {e}"))
            raise
