from inventory.models import Product


def get_category_tree():

    products = Product.objects.filter(
        active=True
    ).values(
        "id",
        "category",
        "subcategory",
        "level3",
        "level4",
        "product_name"
    )


    tree = {}


    for product in products:

        category = product["category"] or "Uncategorized"
        subcategory = product["subcategory"]
        level3 = product["level3"]
        level4 = product["level4"]


        tree.setdefault(
            category,
            {
                "type": "category",
                "children": {}
            }
        )


        current = tree[category]["children"]


        if subcategory:

            current.setdefault(
                subcategory,
                {
                    "type": "subcategory",
                    "children": {}
                }
            )

            current = current[subcategory]["children"]


        if level3:

            current.setdefault(
                level3,
                {
                    "type": "level3",
                    "children": {}
                }
            )

            current = current[level3]["children"]


        if level4:

            current.setdefault(
                level4,
                {
                    "type": "level4",
                    "children": {}
                }
            )

            current = current[level4]["children"]


        current.setdefault(
            "products",
            []
        ).append(
            {
                "id": product["id"],
                "name": product["product_name"]
            }
        )


    return tree