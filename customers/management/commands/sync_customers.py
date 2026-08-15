import os

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from customers.services import import_customer_csv
from inventory.models import SyncHistory, SyncSetting
from inventory.services.google_client import download_customer_csv


class Command(BaseCommand):
    """Download the customer CSV from Google Drive and import it when changed."""

    help = "Sync customers from the Google Drive CSV (only when changed)"

    def handle(self, *args, **options):
        setting = SyncSetting.objects.first()
        if setting is None:
            setting = SyncSetting.objects.create()

        download = download_customer_csv()

        if not download["success"]:
            SyncHistory.objects.create(
                status="FAILED",
                message=download["error"],
            )
            raise CommandError(download["error"])

        filepath = download["filepath"]

        try:
            file_hash = download["hash"]

            # Skip when the sheet hash is unchanged since the last sync.
            if setting.customer_hash == file_hash:
                SyncHistory.objects.create(
                    status="SKIPPED",
                    message="Customer CSV unchanged - no sync needed.",
                )
                self.stdout.write(
                    self.style.WARNING(
                        "Customer CSV unchanged - no sync needed."
                    )
                )
                return

            result = import_customer_csv(filepath)

            setting.customer_hash = file_hash
            setting.last_sync = timezone.now()
            setting.save()

            SyncHistory.objects.create(
                status="SUCCESS",
                message=(
                    f"Customers: {result['customers']}, "
                    f"Invoices: {result['invoices']}, "
                    f"Items: {result['items']}, "
                    f"Deleted: {result['deleted']}"
                ),
            )

            self.stdout.write(self.style.SUCCESS("Customer sync completed."))
            self.stdout.write(f"Customers: {result['customers']}")
            self.stdout.write(f"Invoices: {result['invoices']}")
            self.stdout.write(f"Items: {result['items']}")
            self.stdout.write(f"Deleted: {result['deleted']}")

        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
