from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string

from .models import Product, SyncHistory
from .forms import ProductAdminForm


# Create your views here.
@login_required
def dashboard(request):
    products = Product.objects.filter(
        active=True
    ).order_by("product_name")

    search = request.GET.get("search", "")

    if search:
        products = products.filter(
            product_name__icontains=search
        )

    paginator = Paginator(products, 50)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    last_sync = SyncHistory.objects.first()

    context = {
        "products": page_obj,
        "search": search,
        "last_sync": last_sync,
        "product_count": products.count(),
        "is_admin": request.user.is_staff,
    }

    return render(
        request,
        "inventory/dashboard.html",
        context
    )


@login_required
def product_search(request):
    search = request.GET.get("q", "")

    products = Product.objects.filter(
        active=True,
        product_name__icontains=search
    ).order_by(
        "product_name"
    )[:100]

    context = {
        "products": products,
        "is_admin": request.user.is_staff,
    }

    html = render_to_string(
        "inventory/product_table.html",
        context,
        request=request
    )

    return JsonResponse({
        "html": html
    })


@staff_member_required
@staff_member_required
def edit_product(request, pk):
    product = get_object_or_404(
        Product,
        id=pk,
        active=True
    )

    if request.method == "POST":

        form = ProductAdminForm(
            request.POST,
            instance=product
        )

        if form.is_valid():
            form.save()

            # Recalculate status
            product.calculate_status()
            product.save()

            messages.success(
                request,
                "Product updated successfully."
            )

            return redirect(
                "dashboard"
            )


    else:

        form = ProductAdminForm(
            instance=product
        )

    return render(
        request,
        "inventory/product_edit.html",
        {
            "form": form,
            "product": product,
        }
    )
