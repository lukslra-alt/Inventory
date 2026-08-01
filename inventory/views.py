from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from .models import Product, SyncSetting
from .forms import ProductAdminForm
from inventory.services.category_tree import get_category_tree


@login_required
def dashboard(request):
    """
    Main dashboard controller loading paginated HTML inventory states.
    """
    products = Product.objects.filter(active=True)
    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "")
    subcategory = request.GET.get("subcategory", "")
    level3 = request.GET.get("level3", "")
    level4 = request.GET.get("level4", "")

    if search:
        products = products.filter(
            Q(product_name__icontains=search) |
            Q(category__icontains=search) |
            Q(subcategory__icontains=search) |
            Q(level3__icontains=search) |
            Q(level4__icontains=search) |
            Q(hierarchy_path__icontains=search)
        )
    if category:
        products = products.filter(category=category)
    if subcategory:
        products = products.filter(subcategory=subcategory)
    if level3:
        products = products.filter(level3=level3)
    if level4:
        products = products.filter(level4=level4)

    products = products.order_by("product_name")
    paginator = Paginator(products, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)
    query_string = params.urlencode()

    context = {
        "products": page_obj,
        "page_obj": page_obj,
        "category": category,
        "subcategory": subcategory,
        "level3": level3,
        "level4": level4,
        "category_tree": get_category_tree(),
        "search": search,
        "total_products": Product.objects.filter(active=True).count(),
        "low_stock": Product.objects.filter(active=True, status="LOW").count(),
        "nil_stock": Product.objects.filter(active=True, status="NIL").count(),
        "sync_setting": SyncSetting.objects.first(),
        "show_cost": request.user.is_staff,
        "is_admin": request.user.is_staff,
        "query_string": query_string,
    }
    return render(request, "inventory/dashboard.html", context)


@login_required
def search_products(request):
    """
    Unified asynchronous clean JSON API reflecting exact dashboard filters.
    """
    products = Product.objects.filter(active=True)

    # Read both 'search' and 'q' to handle any variations across frontend scripts smoothly
    search = request.GET.get("search", request.GET.get("q", "")).strip()
    category = request.GET.get("category", "")
    subcategory = request.GET.get("subcategory", "")
    level3 = request.GET.get("level3", "")
    level4 = request.GET.get("level4", "")

    if search:
        products = products.filter(
            Q(product_name__icontains=search) |
            Q(category__icontains=search) |
            Q(subcategory__icontains=search) |
            Q(level3__icontains=search) |
            Q(level4__icontains=search) |
            Q(hierarchy_path__icontains=search)
        )
    if category:
        products = products.filter(category=category)
    if subcategory:
        products = products.filter(subcategory=subcategory)
    if level3:
        products = products.filter(level3=level3)
    if level4:
        products = products.filter(level4=level4)

    products = products.order_by("product_name")

    data = []
    # Bound return limit to 50 for rapid client-side DOM processing
    for product in products[:50]:
        data.append({
            "id": product.id,
            "name": product.product_name,
            "qty": product.qty,
            "price": str(product.sales_price),
            "avg_cost": str(product.avg_cost) if hasattr(product, "avg_cost") else "0.00",
            "status": product.status,
        })

    return JsonResponse({"products": data})


@staff_member_required
def product_edit(request, pk):
    product = get_object_or_404(Product, id=pk, active=True)
    if request.method == "POST":
        form = ProductAdminForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            product.calculate_status()
            product.save()
            messages.success(request, "Product updated successfully.")
            return redirect("dashboard")
    else:
        form = ProductAdminForm(instance=product)

    return render(
        request,
        "inventory/product_edit.html",
        {"form": form, "product": product}
    )


@staff_member_required
def manual_sync(request):
    call_command("sync_inventory")
    messages.success(request, "Inventory sync completed.")
    return redirect("dashboard")


@staff_member_required
def offline_products(request):
    products = Product.objects.all().values("id", "product_name", "category", "sales_price")
    return JsonResponse(list(products), safe=False)
