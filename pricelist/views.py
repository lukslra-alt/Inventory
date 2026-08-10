from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import PricePage, PriceListItem, PriceListHeading
from .forms import PricePageForm, PriceListHeadingForm
from inventory.models import Product
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST


# Shows all categories
@login_required
def price_categories(request):
    pages = PricePage.objects.all()

    return render(
        request,
        'pricelist/categories.html',
        {
            'pages': pages
        }
    )


# Shows one category page
@login_required
def price_page(request, slug):
    page = get_object_or_404(
        PricePage.objects.prefetch_related(
            'items__product',
            'headings'
        ),
        slug=slug
    )

    entries = []

    for item in page.items.all():
        entries.append(
            (item.display_order, "product", item)
        )

    for heading in page.headings.all():
        entries.append(
            (heading.display_order, "heading", heading)
        )

    entries.sort(key=lambda e: e[0])

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
            product = Product.objects.get(
                item=product_id
            )

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


@staff_member_required
def price_manage(request):
    pages = PricePage.objects.prefetch_related(
        'items'
    ).annotate(
        total_items=Count('items'),
        visible_items=Count(
            'items',
            filter=Q(items__visible=True)
        ),
    ).all()

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


def _page_entries(page):
    """
    Returns a list of (display_order, kind, obj) tuples sorted by display_order.
    kind is either "product" (PriceListItem) or "heading" (PriceListHeading).
    """
    entries = []

    for item in page.items.all():
        entries.append(
            (item.display_order, "product", item)
        )

    for heading in page.headings.all():
        entries.append(
            (heading.display_order, "heading", heading)
        )

    entries.sort(key=lambda e: e[0])

    return entries


@staff_member_required
def edit_page(request, page_id):
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
def reorder_page(request, page_id):
    page = get_object_or_404(
        PricePage,
        id=page_id
    )

    order = request.POST.getlist('order')

    for position, entry in enumerate(order, start=1):
        kind, _, obj_id = entry.partition(':')

        if kind == 'product':
            PriceListItem.objects.filter(
                id=obj_id,
                page=page
            ).update(display_order=position)

        elif kind == 'heading':
            PriceListHeading.objects.filter(
                id=obj_id,
                page=page
            ).update(display_order=position)

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def toggle_item(request, page_id):
    kind = request.POST.get('type')
    obj_id = request.POST.get('id')
    visible = request.POST.get('visible') == 'true'

    if kind == 'product':
        PriceListItem.objects.filter(
            id=obj_id,
            page_id=page_id
        ).update(visible=visible)

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def remove_item(request, page_id):
    kind = request.POST.get('type')
    obj_id = request.POST.get('id')

    if kind == 'product':
        PriceListItem.objects.filter(
            id=obj_id,
            page_id=page_id
        ).delete()

    elif kind == 'heading':
        PriceListHeading.objects.filter(
            id=obj_id,
            page_id=page_id
        ).delete()

    return JsonResponse({'ok': True})
