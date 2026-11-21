from django.core.management.base import BaseCommand, CommandError

from inventory.services.google_sync import sync_inventory_from_file


class Command(BaseCommand):
    """Import products from a local QuickBooks or Stock Ageing export."""

    help = (
        "Import products from a local inventory CSV/XLSX file "
        "(QuickBooks export or Stock Ageing Analysis)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=r"D:\COMP0004_StockAgeingAnalysis.xlsx",
            help="Path to the inventory export file",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Import even when the file hash is unchanged",
        )

    def handle(self, *args, **options):
        filepath = options["file"]
        force = options["force"]

        try:
            result = sync_inventory_from_file(filepath, force=force)
        except FileNotFoundError:
            raise CommandError(f"File not found: {filepath}")

        if result["skipped"]:
            self.stdout.write(
                self.style.WARNING(
                    "Inventory file unchanged - no sync needed."
                )
            )
            return

        self.stdout.write(self.style.SUCCESS("Inventory import completed."))
        self.stdout.write(f"Added: {result['added']}")
        self.stdout.write(f"Updated: {result['updated']}")
        self.stdout.write(f"Restored: {result['restored']}")
        self.stdout.write(f"Removed: {result['removed']}")
