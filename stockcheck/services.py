"""Queue and counting logic for random physical stock checks."""

from decimal import Decimal, InvalidOperation

from django.db import transaction

from inventory.models import Product

from .models import StockCheckRecord

BATCH_SIZE = 20
QUEUE_SESSION_KEY = "stock_check_queue"


def counted_item_ids():
    """Product ids that already have a count, so they are never repeated."""
    return set(StockCheckRecord.objects.values_list("product_id", flat=True))


def _session_items(request):
    items = request.session.get(QUEUE_SESSION_KEY, [])
    if not isinstance(items, list):
        return []
    # Preserve order while removing accidental duplicates.
    return list(dict.fromkeys(str(item) for item in items))


def get_batch(request):
    """Return this session's batch, topped up to BATCH_SIZE random products.

    Items already counted, skipped, or deactivated are dropped. Anything left
    uncounted from the previous submission stays at the front of the queue.
    """
    items = _session_items(request)
    counted = counted_item_ids()

    products = {
        product.item: product
        for product in Product.objects.filter(item__in=items)
    }
    queue = [
        products[item]
        for item in items
        if item in products
        and products[item].active
        and not products[item].exclude_from_stock_check
        and item not in counted
    ]

    if len(queue) < BATCH_SIZE:
        taken = {product.item for product in queue}
        candidates = (
            Product.objects.filter(active=True, exclude_from_stock_check=False)
            .exclude(item__in=counted)
            .exclude(item__in=taken)
            .order_by("?")[: BATCH_SIZE - len(queue)]
        )
        queue.extend(candidates)

    request.session[QUEUE_SESSION_KEY] = [product.item for product in queue]
    return queue


@transaction.atomic
def process_batch(request, queue):
    """Save submitted counts and skips; keep blank rows in the queue."""
    counted = 0
    skipped = 0
    invalid = 0
    remaining = []

    for index, product in enumerate(queue):
        if request.POST.get(f"skip_{index}") == "on":
            Product.objects.filter(item=product.item).update(
                exclude_from_stock_check=True
            )
            skipped += 1
            continue

        raw = (request.POST.get(f"qty_{index}") or "").strip()
        if not raw:
            remaining.append(product)
            continue

        try:
            counted_qty = Decimal(raw)
        except (InvalidOperation, ValueError):
            invalid += 1
            remaining.append(product)
            continue

        if counted_qty < 0:
            invalid += 1
            remaining.append(product)
            continue

        counted_qty = counted_qty.quantize(Decimal("0.01"))
        variance = (counted_qty - product.qty).quantize(Decimal("0.01"))

        StockCheckRecord.objects.update_or_create(
            product_id=product.item,
            defaults={
                "system_qty": product.qty,
                "counted_qty": counted_qty,
                "variance": variance,
                "checked_by": request.user,
            },
        )
        counted += 1

    request.session[QUEUE_SESSION_KEY] = [
        product.item for product in remaining
    ]
    return {
        "counted": counted,
        "skipped": skipped,
        "invalid": invalid,
        "remaining": len(remaining),
    }


def clear_queue(request):
    """Discard the current batch so the next page is a fresh random 20."""
    request.session.pop(QUEUE_SESSION_KEY, None)


@transaction.atomic
def reset_history(request):
    """Clear all counted records so those products can be checked again."""
    deleted, _ = StockCheckRecord.objects.all().delete()
    clear_queue(request)
    return deleted
