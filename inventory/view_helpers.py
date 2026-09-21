"""Shared, dependency-free helpers used by the inventory views."""

from django.db.models import Count, Q

from inventory.models import Product

SEARCHABLE_FIELDS = (
    "product_name",
    "category",
    "subcategory",
    "level3",
    "level4",
    "hierarchy_path",
)

DEFAULT_PER_PAGE = 50
MIN_PER_PAGE = 10
MAX_PER_PAGE = 100


def get_product_filters(request):
    """
    Extract the dashboard search/category filters from a request.

    Both ``search`` and ``q`` are honoured so the server-side page and the
    asynchronous frontend script can share the exact same filter rules.
    """
    return {
        "search": request.GET.get("search", request.GET.get("q", "")).strip(),
        "category": request.GET.get("category", ""),
        "subcategory": request.GET.get("subcategory", ""),
        "level3": request.GET.get("level3", ""),
        "level4": request.GET.get("level4", ""),
    }


def apply_product_filters(products, search="", category="", subcategory="", level3="", level4=""):
    """
    Apply dashboard search and category-level filters to a Product queryset.

    The search text is matched against the product name and every level of
    the category hierarchy; the remaining arguments narrow by exact value.
    """
    if search:
        query = Q()
        for field in SEARCHABLE_FIELDS:
            query |= Q(**{f"{field}__icontains": search})
        products = products.filter(query)
    if category:
        products = products.filter(category=category)
    if subcategory:
        products = products.filter(subcategory=subcategory)
    if level3:
        products = products.filter(level3=level3)
    if level4:
        products = products.filter(level4=level4)
    return products


def safe_page_number(value, default=1):
    """
    Parse a page number, returning ``default`` for missing or junk values.

    Negative and zero page numbers are clamped up to ``default`` so a bad
    ``?page=`` parameter can never raise a 500 from the JSON API.
    """
    try:
        return max(int(value), default)
    except (TypeError, ValueError):
        return default


def safe_per_page(value, default=DEFAULT_PER_PAGE):
    """Parse a page size, clamped between MIN_PER_PAGE and MAX_PER_PAGE."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(MIN_PER_PAGE, min(parsed, MAX_PER_PAGE))


def can_view_cost(user):
    """Whether a user may see product cost figures."""
    return bool(user.is_staff or user.is_superuser)


def product_json(product, include_cost=False):
    """Serialize a single active Product for the search/JSON API."""
    payload = {
        "id": product.item,
        "name": product.product_name,
        "qty": product.qty,
        "price": str(product.sales_price),
        "status": product.status,
        "reorder_qty": str(product.reorder_qty),
    }
    if include_cost:
        payload["cost"] = str(product.cost)
    return payload


def stock_summary(active=True):
    """Return total/low/nil stock counters from a single aggregate query."""
    queryset = Product.objects.all()
    if active:
        queryset = queryset.filter(active=True)
    return queryset.aggregate(
        total=Count("item"),
        low=Count("item", filter=Q(status="LOW")),
        nil=Count("item", filter=Q(status="NIL")),
    )