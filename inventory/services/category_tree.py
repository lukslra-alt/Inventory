"""Build the category hierarchy tree shown on the inventory dashboard."""

from inventory.models import Product


def get_category_tree():
    """
    Group active products into a nested category/subcategory/level tree.

    Returns a dict whose top-level keys are category names. Each node is a
    dict with a "type" (category/subcategory/level3/level4) and a "children"
    mapping, where "products" holds the list of products grouped at that
    level.
    """
    tree = {}

    products = Product.objects.filter(active=True).order_by(
        "category",
        "subcategory",
        "level3",
        "level4",
        "product_name"
    )

    for p in products:

        category = p.category or "Uncategorized"
        subcategory = p.subcategory or ""
        level3 = p.level3 or ""
        level4 = p.level4 or ""

        cat = tree.setdefault(category, {
            "type": "category",
            "category": category,
            "children": {}
        })

        current = cat["children"]

        # Descend one level at a time, creating nodes only when the level
        # actually has a value for this product.
        if subcategory:
            sub = current.setdefault(subcategory, {
                "type": "subcategory",
                "category": category,
                "subcategory": subcategory,
                "children": {}
            })

            current = sub["children"]

        if level3:
            l3 = current.setdefault(level3, {
                "type": "level3",
                "category": category,
                "subcategory": subcategory,
                "level3": level3,
                "children": {}
            })

            current = l3["children"]

        if level4:
            l4 = current.setdefault(level4, {
                "type": "level4",
                "category": category,
                "subcategory": subcategory,
                "level3": level3,
                "level4": level4,
                "children": {}
            })

            current = l4["children"]

        current.setdefault("products", []).append({
            "id": p.item,
            "product_name": p.product_name
        })

    return tree
