from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from inventory.models import Product


@transaction.atomic
def sync_products(products):
    """
    Upsert products from a parsed inventory export.

    - Sheet-controlled fields (category, qty, cost, etc.) are overwritten.
    - sales_price and reorder_qty are local admin fields — never touched.
    - Products missing from the sheet are soft-deleted (active=False).
    - Products that reappear after soft-delete are restored (active=True).
    - Stock Ageing rows match by product name and preserve the stored
      category hierarchy; a derived cost is applied only when the report
      actually carries a value.
    """

    sheet_items = set()
    used_items = set()

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

        product = None

        if product_data.get("match_by") == "product_name":
            # Stock Ageing reports carry names only, not item paths. Match
            # existing products so admin fields and hierarchy survive.
            name = str(product_data.get("product_name", item)).strip()
            product = (
                Product.objects
                .filter(product_name=name, active=True)
                .order_by("item")
                .first()
            )

            if product is None and len(name) >= 20:
                # Tally truncates long names. Accept a single unambiguous
                # prefix match to avoid creating duplicate products.
                matches = list(
                    Product.objects
                    .filter(product_name__startswith=name, active=True)
                    .order_by("item")[:5]
                )
                if len(matches) == 1:
                    product = matches[0]

            if product is None:
                # Fall back to an inactive record so it can be restored.
                product = (
                    Product.objects
                    .filter(product_name=name)
                    .order_by("item")
                    .first()
                )

            if product is not None and product.item in used_items:
                continue

            if product is not None:
                used_items.add(product.item)
                item = product.item
        else:
            product = Product.objects.filter(item=item).first()

        sheet_items.add(item)

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
                    str(product_data.get("cost") or "0.00")
                ),

                # Admin-only fields — defaults until set in the dashboard.
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

        # Stock Ageing has no category path and may truncate long names,
        # so keep the identity fields already stored for matched products.
        if not product_data.get("preserve_identity"):

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

        # None means the source has no value for this item, so keep the
        # cost already stored instead of wiping it to zero.
        if product_data.get("cost") is not None:

            cost = Decimal(
                str(product_data["cost"])
            )

            if product.cost != cost:

                product.cost = cost

                changed = True

        # =========================================
        # RESTORE
        # =========================================

        # Reappeared in sheet after a previous soft-delete.
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

    # QuickBooks exports list every catalogue item, so absences mean the
    # product is gone and should be soft-deleted. Stock Ageing reports only
    # list items holding stock, so absences mean zero quantity instead.
    missing = (
        Product.objects
        .filter(active=True)
        .exclude(item__in=sheet_items)
    )

    deactivate_missing = not any(
        data.get("deactivate_missing") is False
        for data in products
    )

    if deactivate_missing:
        # Records are kept so admin pricing and history are preserved.
        removed = missing.update(
            active=False,
            updated_at=timezone.now(),
        )
    else:
        missing.update(
            qty=Decimal("0.00"),
            status="NIL",
            updated_at=timezone.now(),
        )
        removed = 0

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