from decimal import Decimal

from django.db import transaction

from inventory.models import Product


@transaction.atomic
def sync_products(products):

    sheet_products = set()

    added = 0
    updated = 0
    restored = 0

    for item in products:

        product_name = item["product_name"].strip()

        sheet_products.add(product_name)

        product = Product.objects.filter(
            product_name=product_name
        ).first()

        if product is None:

            Product.objects.create(

                product_name=product_name,

                category=item["category"],

                subcategory=item["subcategory"],

                level3=item["level3"],

                level4=item["level4"],

                qty=Decimal(str(item["qty"])),

                avg_cost=Decimal(str(item["avg_cost"])),

                sales_price=Decimal("0.00"),

                reorder_qty=Decimal("0.00"),

                active=True

            )

            added += 1

        else:

            changed = False

            if product.category != item["category"]:
                product.category = item["category"]
                changed = True

            if product.subcategory != item["subcategory"]:
                product.subcategory = item["subcategory"]
                changed = True

            if product.level3 != item["level3"]:
                product.level3 = item["level3"]
                changed = True

            if product.level4 != item["level4"]:
                product.level4 = item["level4"]
                changed = True

            qty = Decimal(str(item["qty"]))

            if product.qty != qty:
                product.qty = qty
                changed = True

            avg_cost = Decimal(str(item["avg_cost"]))

            if product.avg_cost != avg_cost:
                product.avg_cost = avg_cost
                changed = True

            if not product.active:
                product.active = True
                restored += 1
                changed = True

            if changed:
                product.save()
                updated += 1

    removed = 0

    for product in Product.objects.filter(active=True):

        if product.product_name not in sheet_products:

            product.active = False

            product.save()

            removed += 1

    return {

        "added": added,

        "updated": updated,

        "restored": restored,

        "removed": removed,

        "total_products": len(sheet_products),

    }