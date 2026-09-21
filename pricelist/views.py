"""
Price list app views: public category browsing plus staff management and PDF.

Public pages are guarded by pricelist_required; management endpoints are
restricted to staff and mostly return small JSON responses consumed by the
management UI's drag-and-drop ordering.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import PricePage, PriceListItem, PriceListHeading
from .forms import PricePageForm, PriceListHeadingForm
from inventory.models import Product
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache

from usermanage.roles import pricelist_required

from .pdf import _page_entries, price_page_pdf_bytes

from decimal import Decimal, InvalidOperation


def _safe_int(value):
    """
    Return an int for the given value, or None when it is junk.

    Management endpoints accept ids from POST bodies; a non-numeric value
    would raise ValueError inside an IntegerField lookup and return a 500,
    so callers should skip entries that fail this guard.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# Shows all categories
@never_cache
@pricelist_required
def price_categories(request):
    """Landing page listing every price list category."""
    pages = PricePage.objects.all()

    return render(
        request,
        'pricelist/categories.html',
        {
            'pages': pages
        }
    )


# Shows one category page
@never_cache
@pricelist_required
def price_page(request, slug):
    """Render a single price page with its items and headings in order."""
    page = get_object_or_404(
        PricePage.objects.prefetch_related(
            'items__product',
            'headings'
        ),
        slug=slug
    )

    entries = _page_entries(page)

    return render(
        request,
        'pricelist/price_page.html',
        {
            'page': page,
            'entries': entries
        }
    )


@staff_member_required
def add_heading(request, page_id):
    """Add a section heading to a price page."""
    page = get_object_or_404(
        PricePage,
        id=page_id
    )

    if request.method == "POST":
        form = PriceListHeadingForm(request.POST)

        if form.is_valid():
            heading = form.save(commit=False)
            heading.page = page
            heading.save()

            messages.success(
                request,
                f'Heading "{heading.text}" added to {page.name}.'
            )

            return redirect('price_manage')

    else:
        form = PriceListHeadingForm()

    return render(
        request,
        'pricelist/add_heading.html',
        {
            'form': form,
            'page': page,
        }
    )


@login_required
@staff_member_required
def add_products(request, page_id):
    """Search products and attach selected ones to a price page."""
    page = get_object_or_404(
        PricePage,
        id=page_id
    )

    products = []

    search = request.GET.get('search', '')

    if search:
        products = Product.objects.filter(
            product_name__icontains=search
        ).order_by("product_name")

    if request.method == "POST":

        selected_products = request.POST.getlist(
            'products'
        )

        for product_id in selected_products:
            product = Product.objects.filter(
                item=product_id
            ).first()

            if product is None:
                continue

            # get_or_create keeps repeated adds from duplicating entries.
            PriceListItem.objects.get_or_create(
                page=page,
                product=product
            )

        messages.success(
            request,
            f"Added {len(selected_products)} product(s) to {page.name}."
        )

        return redirect(
            'price_manage'
        )

    added_items = set(
        PriceListItem.objects.filter(
            page=page
        ).values_list("product_id", flat=True)
    )

    return render(
        request,
        'pricelist/add_products.html',
        {
            'page': page,
            'products': products,
            'search': search,
            'added_items': added_items,
        }
    )


@staff_member_required
def add_category(request):
    """Create a new price page/category."""
    if request.method == "POST":
        form = PricePageForm(request.POST)

        if form.is_valid():
            page = form.save()
            messages.success(
                request,
                f'Category "{page.name}" created.',
            )
            return redirect("price_manage")

    else:
        form = PricePageForm()

    return render(
        request,
        "pricelist/add_category.html",
        {
            "form": form,
        }
    )


@never_cache
@staff_member_required
def price_manage(request):
    """Management overview of pages with item and visibility totals."""
    pages = PricePage.objects.prefetch_related(
        'items'
    ).annotate(
        total_items=Count('items'),
        visible_items=Count(
            'items',
            filter=Q(items__visible=True)
        ),
    ).order_by('display_order', 'id')

    total_pages = pages.count()
    total_items = sum(p.total_items for p in pages)
    visible_items = sum(p.visible_items for p in pages)

    return render(
        request,
        'pricelist/manage_categories.html',
        {
            'pages': pages,
            'total_pages': total_pages,
            'total_items': total_items,
            'visible_items': visible_items,
        }
    )


@staff_member_required
def edit_page(request, page_id):
    """Edit page contents: add products by search and reorder headings/items."""
    page = get_object_or_404(
        PricePage.objects.prefetch_related(
            'items__product',
            'headings'
        ),
        id=page_id
    )

    if request.method == "POST":
        selected_products = request.POST.getlist(
            'products'
        )

        added = 0

        for product_id in selected_products:
            product = Product.objects.filter(
                item=product_id
            ).first()

            if not product:
                continue

            _, created = PriceListItem.objects.get_or_create(
                page=page,
                product=product
            )

            if created:
                added += 1

        messages.success(
            request,
            f"Added {added} product(s) to {page.name}."
        )

        return redirect('edit_page', page_id=page.id)

    search = request.GET.get('search', '')

    results = Product.objects.none()

    if search:
        results = Product.objects.filter(
            product_name__icontains=search
        ).order_by("product_name")

    added_ids = set(
        page.items.values_list("product_id", flat=True)
    )

    return render(
        request,
        'pricelist/edit_page.html',
        {
            'page': page,
            'entries': _page_entries(page),
            'search': search,
            'results': results,
            'added_ids': added_ids,
        }
    )


@staff_member_required
@require_POST
def update_item_price(request, page_id):
    """
    Update product sales prices from the edit page.

    Prices are sent as a list of "item_id:price" strings. Each change is
    written to the product's sales_price so it applies everywhere the
    product appears (dashboard, PDFs, every price page).
    """
    page = get_object_or_404(
        PricePage,
        id=page_id
    )

    updated = 0
    errors = 0

    for entry in request.POST.getlist("prices"):
        item_id, _, raw = entry.partition(":")

        numeric_id = _safe_int(item_id)

        if numeric_id is None:
            errors += 1
            continue

        try:
            price = Decimal(raw.strip())
        except (InvalidOperation, AttributeError):
            errors += 1
            continue

        if price < 0:
            errors += 1
            continue

        item = PriceListItem.objects.filter(
            id=numeric_id,
            page=page,
        ).select_related("product").first()

        if item is None:
            continue

        product = item.product

        if product.sales_price != price:
            # Only sales_price changes here; a full save() would needlessly
            # rebuild the hierarchy path and recompute stock status.
            Product.objects.filter(pk=product.pk).update(sales_price=price)
            updated += 1

    return JsonResponse({"ok": True, "updated": updated, "errors": errors})


@staff_member_required
@require_POST
def reorder_page(request, page_id):
    """Persist the new drag-and-drop order of a page's items and headings."""
    page = get_object_or_404(
        PricePage,
        id=page_id
    )

    # POST order entries are encoded as "kind:id", e.g. "product:12".
    order = request.POST.getlist('order')

    for position, entry in enumerate(order, start=1):
        kind, _, obj_id = entry.partition(':')

        numeric_id = _safe_int(obj_id)

        if numeric_id is None:
            continue

        if kind == 'product':
            PriceListItem.objects.filter(
                id=numeric_id,
                page=page
            ).update(display_order=position)

        elif kind == 'heading':
            PriceListHeading.objects.filter(
                id=numeric_id,
                page=page
            ).update(display_order=position)

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def toggle_item(request, page_id):
    """Toggle visibility of an item on a page (used by the manage UI)."""
    kind = request.POST.get('type')
    obj_id = _safe_int(request.POST.get('id'))
    visible = request.POST.get('visible') == 'true'

    if kind == 'product' and obj_id is not None:
        PriceListItem.objects.filter(
            id=obj_id,
            page_id=page_id
        ).update(visible=visible)

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def remove_item(request, page_id):
    """Remove an item or heading from a page."""
    kind = request.POST.get('type')
    obj_id = _safe_int(request.POST.get('id'))

    if kind == 'product' and obj_id is not None:
        PriceListItem.objects.filter(
            id=obj_id,
            page_id=page_id
        ).delete()

    elif kind == 'heading' and obj_id is not None:
        PriceListHeading.objects.filter(
            id=obj_id,
            page_id=page_id
        ).delete()

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def reorder_categories(request):
    """Persist the new drag-and-drop order of the category pages."""
    order = request.POST.getlist('order')

    for position, page_id in enumerate(order, start=1):
        numeric_id = _safe_int(page_id)

        if numeric_id is None:
            continue

        PricePage.objects.filter(
            id=numeric_id
        ).update(display_order=position)

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def rename_category(request):
    """Rename a price page/category via the manage UI."""
    page_id = _safe_int(request.POST.get('id'))
    name = (request.POST.get('name') or '').strip()

    if page_id is None or not name:
        return JsonResponse(
            {'ok': False, 'error': 'Category name is required'}
        )

    page = get_object_or_404(
        PricePage,
        id=page_id
    )

    page.name = name
    page.save()

    return JsonResponse({'ok': True})


@pricelist_required
def price_page_pdf(request, slug):
    """Generate a printable PDF price list for a page, 1-3 newspaper columns."""
    page = get_object_or_404(
        PricePage.objects.prefetch_related(
            'items__product',
            'headings'
        ),
        slug=slug
    )

    # Column count is user-tunable via ?cols=1|2|3 and clamped safely.
    try:
        cols = max(1, min(int(request.GET.get('cols', 1)), 3))
    except (TypeError, ValueError):
        cols = 1

    pdf = price_page_pdf_bytes(page, cols)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="pricelist-{page.slug}.pdf"'
    )
    return response
