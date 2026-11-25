from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0016_product_product_qty_non_negative_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="product",
            name="product_qty_non_negative",
        ),
    ]
