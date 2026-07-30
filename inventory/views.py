from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.contrib import messages

from .models import Product, SyncSetting
from .forms import ProductAdminForm
from inventory.services.category_tree import get_category_tree


# Create your views here.
@login_required
def dashboard(request):
    products = Product.objects.filter(
        active=True
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    category = request.GET.get(
        "category",
        ""
    )

    subcategory = request.GET.get(
        "subcategory",
        ""
    )

    level3 = request.GET.get(
        "level3",
        ""
    )

    level4 = request.GET.get(
        "level4",
        ""
    )

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
        products = products.filter(
            category=category
        )

    if subcategory:
        products = products.filter(
            subcategory=subcategory
        )

    if level3:
        products = products.filter(
            level3=level3
        )

    if level4:
        products = products.filter(
            level4=level4
        )

    products = products.order_by(
        "product_name"
    )

    paginator = Paginator(
        products,
        50
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    context = {

        "products": page_obj,

        "page_obj": page_obj,

        "category_tree": get_category_tree(),

        "search": search,

        "total_products": Product.objects.filter(
            active=True
        ).count(),

        "low_stock": Product.objects.filter(
            active=True,
            status="LOW"
        ).count(),

        "nil_stock": Product.objects.filter(
            active=True,
            status="NIL"
        ).count(),

        "sync_setting": SyncSetting.objects.first(),

        "show_cost": request.user.is_staff,

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
def product_edit(request, pk):
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


@staff_member_required
def manual_sync(request):
    call_command(
        "sync_inventory"
    )

    messages.success(
        request,
        "Inventory sync completed."
    )

    return redirect(
        "dashboard"
    )


@login_required
def search_products(request):
    query = request.GET.get("q", "").strip()

    products = Product.objects.filter(
        active=True
    )

    category = request.GET.get(
        "category",
        ""
    )

    subcategory = request.GET.get(
        "subcategory",
        ""
    )

    level3 = request.GET.get(
        "level3",
        ""
    )

    level4 = request.GET.get(
        "level4",
        ""
    )

    if category:
        products = products.filter(
            category=category
        )

    if subcategory:
        products = products.filter(
            subcategory=subcategory
        )

    if level3:
        products = products.filter(
            level3=level3
        )

    if level4:
        products = products.filter(
            level4=level4
        )

    if query:
        products = products.filter(

            Q(product_name__icontains=query) |

            Q(category__icontains=query) |

            Q(subcategory__icontains=query) |

            Q(level3__icontains=query) |

            Q(level4__icontains=query)

        )

    data = []

    for product in products[:50]:
        data.append({

            "id": product.id,
            "name": product.product_name,
            "qty": product.qty,
            "price": product.sales_price,
            "status": product.status,

        })

    return JsonResponse(
        {
            "products": data
        }
    )
