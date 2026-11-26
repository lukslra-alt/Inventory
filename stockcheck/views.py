"""Views for random physical stock checks."""

from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from inventory.models import Product

from . import services
from .models import StockCheckRecord


def staff_check_required(view_func):
    """Stock checks are staff-only; customers go back to their list."""

    @wraps(view_func)
    @login_required(login_url=settings.LOGIN_URL)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect("customer_list")
        return view_func(request, *args, **kwargs)

    return _wrapped


@staff_check_required
def stock_check(request):
    """Show a random batch of 20 and save submitted counts or skips."""
    if request.method == "POST":
        if request.POST.get("action") == "new_batch":
            services.clear_queue(request)
            messages.info(request, "Started a new random batch.")
            return redirect("stock_check")

        queue = services.get_batch(request)
        result = services.process_batch(request, queue)

        if result["invalid"]:
            messages.error(
                request,
                f'{result["invalid"]} invalid quantity values were left in '
                "the queue.",
            )
        messages.success(
            request,
            f'Counted {result["counted"]}, skipped {result["skipped"]}. '
            f'{result["remaining"]} item(s) remain in the queue.',
        )
        return redirect("stock_check")

    batch = services.get_batch(request)
    excluded = Product.objects.filter(
        exclude_from_stock_check=True
    ).order_by("product_name")
    excluded_page = Paginator(excluded, 25).get_page(
        request.GET.get("excluded_page")
    )

    return render(
        request,
        "stockcheck/stock_check.html",
        {
            "batch": batch,
            "batch_size": services.BATCH_SIZE,
            "counted_total": StockCheckRecord.objects.count(),
            "excluded_total": excluded.count(),
            "excluded_page": excluded_page,
        },
    )


@staff_check_required
@require_POST
def reset_checks(request):
    """Clear the counted history so those items may be checked again."""
    deleted = services.reset_history(request)
    messages.success(
        request,
        f"Cleared {deleted} counted record(s). Those products can be "
        "checked again.",
    )
    return redirect("stock_check")


@staff_check_required
@require_POST
def restore_product(request):
    """Remove a product's permanent 'no need to check' flag."""
    item = (request.POST.get("item") or "").strip()
    updated = Product.objects.filter(
        item=item, exclude_from_stock_check=True
    ).update(exclude_from_stock_check=False)

    if updated:
        messages.success(request, "Product restored to the check queue.")
    else:
        messages.info(request, "That product was not excluded.")

    return redirect("stock_check")
