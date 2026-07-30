from django import forms
from .models import Product


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product

        fields = [
            "sales_price",
            "reorder_qty",
        ]

        widgets = {
            "sales_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "reorder_qty": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "1",
                    "min": "0",
                }
            ),
        }

    def clean_sales_price(self):

        value = self.cleaned_data["sales_price"]

        if value < 0:
            raise forms.ValidationError(
                "Sales price cannot be negative."
            )

        return value

    def clean_reorder_qty(self):

        value = self.cleaned_data["reorder_qty"]

        if value < 0:
            raise forms.ValidationError(
                "Reorder quantity cannot be negative."
            )

        return value
