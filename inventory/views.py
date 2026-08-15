"""Views for the inventory app: dashboard, product search and sync pages."""

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from .models import Product, SyncSetting, SyncHistory
from .forms import ProductAdminForm
from inventory.services.category_tree import get_category_tree
from usermanage.roles import admin_required


def apply_product_filters(products, search="", category="", subcategory="", level3="", level4=""):
    """
    Apply dashboard search and category-level filters to a Product queryset.

    The search text is matched against the product name and every level of
    the category hierarchy; the remaining arguments narrow by exact value.
    """
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
    return products


def count_tree_products(node):
    """Recursively count products nested under a category-tree node."""
    total = 0
    children = node.get("children", {}) or {}
    total += len(children.get("products", []) or [])
    for key, child in children.items():
        if key == "products":
            continue
        total += count_tree_products(child)
    return total


@login_required
def dashboard(request):
    """
    Main dashboard controller loading paginated HTML inventory states.
    """
    if not request.user.is_staff:
        return redirect("customer_list")

    products = Product.objects.filter(active=True)
    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "")
    subcategory = request.GET.get("subcategory", "")
    level3 = request.GET.get("level3", "")
    level4 = request.GET.get("level4", "")

    products = apply_product_filters(
        products, search, category, subcategory, level3, level4
    )

    products = products.order_by("product_name")
    paginator = Paginator(products, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)
    query_string = params.urlencode()

    tree = get_category_tree()
    emoji_palette = [
        "📦", "🍎", "🥖", "🥤", "🧴", "🧹", "🍞", "🥛",
        "🍫", "🍚", "🛒", "🧃", "🧇", "🥫", "🍪", "🍬",
    ]
    category_icons = []
    for i, (key, node) in enumerate(tree.items()):
        if key == "products":
            continue
        category_icons.append({
            "name": key,
            "icon": emoji_palette[i % len(emoji_palette)],
        })

    subcategory_icons = []
    if category and category in tree:
        for sub_key, sub_node in tree[category].get("children", {}).items():
            if sub_key == "products":
                continue
            # Only show as a subheading when it actually groups multiple
            # products. Single-product "subcategories" whose name equals the
            # product name are really just products and should not appear
            # as a heading (the product is already listed below).
            if sub_node.get("type") == "subcategory" and count_tree_products(sub_node) > 1:
                subcategory_icons.append(sub_key)

    context = {
        "products": page_obj,
        "page_obj": page_obj,
        "category": category,
        "subcategory": subcategory,
        "level3": level3,
        "level4": level4,
        "category_tree": tree,
        "category_icons": category_icons,
        "subcategory_icons": subcategory_icons,
        "search": search,
        "total_products": Product.objects.filter(active=True).count(),
        "low_stock": Product.objects.filter(active=True, status="LOW").count(),
        "nil_stock": Product.objects.filter(active=True, status="NIL").count(),
        "reorder_count": Product.objects.filter(
            active=True, status__in=["LOW", "NIL"]
        ).count(),
        "sync_setting": SyncSetting.objects.first(),
        "show_cost": request.user.is_staff or request.user.is_superuser,
        "is_admin": request.user.is_staff or request.user.is_superuser,
        "query_string": query_string,
    }
    return render(request, "inventory/dashboard.html", context)


@staff_member_required
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

    products = apply_product_filters(
        products, search, category, subcategory, level3, level4
    ).order_by("product_name")

    data = []
    # Bound return limit to 50 for rapid client-side DOM processing
    for product in products[:50]:
        entry = {
            "id": product.item,
            "name": product.product_name,
            "qty": product.qty,
            "price": str(product.sales_price),
            "status": product.status,
            "reorder_qty": str(product.reorder_qty),
        }
        if (request.user.is_staff or request.user.is_superuser) and hasattr(product, "cost"):
            entry["cost"] = str(product.cost)
        data.append(entry)

    return JsonResponse({"products": data})


@staff_member_required
def product_edit(request, pk):
    """Inline admin form for editing a single product."""
    product = get_object_or_404(Product, item=pk, active=True)
    if request.method == "POST":
        form = ProductAdminForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            # Recompute LOW/NIL stock status after the edit.
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


@admin_required
def manual_sync(request):
    """Run both inventory and customer sync commands in one request."""
    try:
        call_command("sync_inventory")
        call_command("sync_customers")
        messages.success(request, "Inventory and customer sync completed.")
    except Exception as error:
        messages.error(request, f"Sync failed: {error}")
    return redirect("sync_page")


@admin_required
def sync_page(request):
    """Sync dashboard showing the sync setting and recent history."""
    setting = SyncSetting.objects.first()

    return render(
        request,
        "inventory/sync_page.html",
        {
            "sync_setting": setting,
            "history": SyncHistory.objects.order_by("-sync_time")[:20],
        }
    )


@admin_required
def sync_products(request):
    """Trigger the product sync command and report the outcome."""
    try:
        call_command("sync_inventory")
        messages.success(request, "Product sync completed.")
    except Exception as error:
        messages.error(request, f"Product sync failed: {error}")
    return redirect("sync_page")


@admin_required
def sync_customers(request):
    """Trigger the customer sync command and report the outcome."""
    try:
        call_command("sync_customers")
        messages.success(request, "Customer sync completed.")
    except Exception as error:
        messages.error(request, f"Customer sync failed: {error}")
    return redirect("sync_page")


@staff_member_required
def offline_products(request):
    """Expose all active products as JSON for offline caching (PWA)."""
    fields = [
        "item", "product_name", "category", "subcategory", "level3", "level4",
        "hierarchy_path", "sales_price", "qty", "reorder_qty", "status",
    ]
    # Cost is sensitive, so only expose it to staff/superusers.
    if (request.user.is_staff or request.user.is_superuser):
        fields.append("cost")
    products = Product.objects.filter(active=True).values(*fields)
    return JsonResponse(list(products), safe=False)
