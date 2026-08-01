from django.shortcuts import render, get_object_or_404, redirect
from .models import PricePage, PriceListItem
from inventory.models import Product
from django.contrib.admin.views.decorators import staff_member_required


# Shows all categories
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
        )

    if request.method == "POST":

        selected_products = request.POST.getlist(
            'products'
        )

        for product_id in selected_products:
            product = Product.objects.get(
                id=product_id
            )

            PriceListItem.objects.get_or_create(
                page=page,
                product=product
            )

        return redirect(
            'admin:pricelist_pricepage_change',
            page.id
        )

    return render(
        request,
        'pricelist/add_products.html',
        {
            'page': page,
            'products': products,
            'search': search
        }
    )


@staff_member_required
def price_manage(request):
    pages = PricePage.objects.prefetch_related(
        'items'
    ).all()

    return render(
        request,
        'pricelist/manage_categories.html',
        {
            'pages': pages
        }
    )
