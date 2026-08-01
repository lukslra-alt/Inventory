from django.core.management.base import BaseCommand
from django.conf import settings
import os

from inventory.services.qb_parser import QuickBooksParser
from inventory.services.sync_engine import sync_products
from inventory.models import SyncHistory


class Command(BaseCommand):
    help = "Synchronize inventory from Excel"

    def handle(self, *args, **options):

        excel_file = os.path.join(
            settings.BASE_DIR,
            "data",
            "inventory.xlsx"
        )

        if not os.path.exists(excel_file):
            self.stdout.write(
                self.style.ERROR(
                    f"Excel file not found:\n{excel_file}"
                )
            )
            return

        try:
            self.stdout.write("Reading Excel...")

            parser = QuickBooksParser(excel_file)

            products = parser.parse()

            result = sync_products(products)

            SyncHistory.objects.create(
                added_count=result["added"],
                updated_count=result["updated"],
                restored_count=result["restored"],
                removed_count=result["removed"],
                status="SUCCESS",
                message="Synchronization completed."
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Synchronization completed successfully."
                )
            )

            self.stdout.write(
                f"Added: {result['added']}"
            )

            self.stdout.write(
                f"Updated: {result['updated']}"
            )

            self.stdout.write(
                f"Restored: {result['restored']}"
            )

            self.stdout.write(
                f"Removed: {result['removed']}"
            )

            self.stdout.write(
                f"Products in Excel: {result['total_products']}"
            )

        except Exception as e:

            SyncHistory.objects.create(
                status="FAILED",
                message=str(e)
            )

            self.stdout.write(
                self.style.ERROR(str(e))
            )

            raise
