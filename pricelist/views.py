from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import PricePage, PriceListItem
from .forms import PricePageForm
from inventory.models import Product
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q


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
            'items__product'
        ),
        slug=slug
    )

    return render(
        request,
        'pricelist/price_page.html',
        {
            'page': page
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
