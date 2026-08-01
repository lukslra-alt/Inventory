from inventory.models import Product

from inventory.models import Product


def get_category_tree():
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
            "id": p.id,
            "product_name": p.product_name
        })

    return tree
