import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand

from inventory.models import Product


class Command(BaseCommand):
    help = "Update product sales prices from a CSV file (ITEMS, FINAL LP columns)"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Path to the CSV file")
        parser.add_argument(
            "--brand", default="NACHI",
            help="Brand to match in DB (default: NACHI)",
        )

    def _find_product(self, item_code, brand):
        """
        Find a product whose name matches the CSV item code for the given brand.

        DB product names follow the pattern ``<code> - BRAND`` with
        occasional spacing variations, so we try several forms.
        """
        for sep in (" - ", "- ", " -", "-"):
            name = f"{item_code}{sep}{brand}"
            product = Product.objects.filter(
                product_name=name,
                item__icontains=brand,
            ).first()
            if product:
                return product

        # Partial fallback: product name starts with the code and is the
        # requested brand.
        product = Product.objects.filter(
            item__icontains=brand,
            product_name__startswith=item_code,
        ).first()
        if product and brand.upper() in (product.product_name or "").upper():
            return product

        return None

    def handle(self, *args, **options):
        filepath = options["csv_file"]
        brand = options["brand"]

        matched = 0
        updated = 0
        skipped_price = 0
        not_found = 0
        not_found_items = []

        with open(filepath, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)

            for row in reader:
                item_code = (row.get("ITEMS") or "").strip()

                # Skip repeated header rows in multi-page CSVs
                if not item_code or item_code == "ITEMS":
                    continue

                raw_price = (row.get("FINAL LP") or "").strip()

                try:
                    price = Decimal(raw_price.replace(",", ""))
                except (InvalidOperation, ValueError):
                    skipped_price += 1
                    continue

                if price <= 0:
                    skipped_price += 1
                    continue

                product = self._find_product(item_code, brand)

                if product is None:
                    not_found += 1
                    not_found_items.append(item_code)
                    continue

                matched += 1

                if product.sales_price != price:
                    product.sales_price = price
                    product.save()
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done.\n"
            f"  Matched in DB: {matched}\n"
            f"  Prices updated: {updated}\n"
            f"  Not in DB: {not_found}\n"
            f"  Bad price rows: {skipped_price}"
        ))

        if not_found_items:
            self.stdout.write("\nItems not found in database:")
            for code in not_found_items:
                self.stdout.write(f"  {code}")
