from django.core.management.base import BaseCommand, CommandError

from customers.services import import_customer_csv


class Command(BaseCommand):
    """Import customers, invoices and items from a customer/bills CSV."""

    help = (
        "Import customers, invoices and items from a QuickBooks customer "
        "export or a Tally-style bills receivable CSV"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="D:\\Customer.CSV",
            help="Path to the customer CSV file",
        )

    def handle(self, *args, **options):
        filepath = options["file"]

        try:
            result = import_customer_csv(filepath)
        except FileNotFoundError:
            raise CommandError(f"File not found: {filepath}")

        # Report how many records were written per entity type.
        self.stdout.write(self.style.SUCCESS("Customer import completed."))
        self.stdout.write(f"Customers added: {result['customers']}")
        self.stdout.write(f"Invoices added: {result['invoices']}")
        self.stdout.write(f"Items added: {result['items']}")
        self.stdout.write(f"Paid/closed invoices removed: {result['deleted_invoices']}")
