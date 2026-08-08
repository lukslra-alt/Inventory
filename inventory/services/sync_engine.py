from decimal import Decimal

from django.db import transaction

from inventory.models import Product


@transaction.atomic
def sync_products(products):

    sheet_items = set()

    added = 0
    updated = 0
    restored = 0

    for product_data in products:

        # =========================================
        # GET ITEM / PRIMARY KEY
        # =========================================

        item = str(
            product_data["item"]
        ).strip()

        if not item:
            continue

        sheet_items.add(item)

        product = Product.objects.filter(
            item=item
        ).first()

        # =========================================
        # NEW PRODUCT
        # =========================================

        if product is None:

            Product.objects.create(

                item=item,

                product_name=product_data["product_name"],

                category=product_data["category"],

                subcategory=product_data["subcategory"],

                level3=product_data["level3"],

                level4=product_data["level4"],

                hierarchy_path=product_data["hierarchy_path"],

                qty=Decimal(
                    str(product_data["qty"])
                ),

                cost=Decimal(
                    str(product_data["cost"])
                ),

                # LOCAL ADMIN VALUES
                sales_price=Decimal("0.00"),

                reorder_qty=Decimal("0.00"),

                active=True,

            )

            added += 1

            continue

        # =========================================
        # EXISTING PRODUCT
        # =========================================

        changed = False

        fields = (
            "product_name",
            "category",
            "subcategory",
            "level3",
            "level4",
            "hierarchy_path",
        )

        for field in fields:

            new_value = product_data[field]

            if getattr(product, field) != new_value:

                setattr(
                    product,
                    field,
                    new_value
                )

                changed = True

        # =========================================
        # QUANTITY
        # =========================================

        qty = Decimal(
            str(product_data["qty"])
        )

        if product.qty != qty:

            product.qty = qty

            changed = True

        # =========================================
        # COST
        # =========================================

        cost = Decimal(
            str(product_data["cost"])
        )

        if product.cost != cost:

            product.cost = cost

            changed = True

        # =========================================
        # RESTORE
        # =========================================

        if not product.active:

            product.active = True

            restored += 1

            changed = True

        # =========================================
        # SAVE
        # =========================================

        if changed:

            product.save()

            updated += 1

    # =========================================
    # REMOVE PRODUCTS NO LONGER IN SHEET
    # =========================================

    removed = 0

    for product in Product.objects.filter(
        active=True
    ):

        if product.item not in sheet_items:

            product.active = False

            product.save()

            removed += 1

    # =========================================
    # RETURN RESULT
    # =========================================

    return {

        "added": added,

        "updated": updated,

        "restored": restored,

        "removed": removed,

        "total_products": len(sheet_items),

    }