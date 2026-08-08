from django import forms
from django.utils.text import slugify

from .models import PricePage


class PricePageForm(forms.ModelForm):
    class Meta:
        model = PricePage
        fields = [
            "name",
            "slug",
            "display_order",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. N70 Polisher",
                }
            ),
            "slug": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Leave blank to auto-generate from name",
                }
            ),
            "display_order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
        }

    def clean(self):
        cleaned = super().clean()

        name = cleaned.get("name")
        slug = cleaned.get("slug")

        # Auto-generate a slug from the name when none is supplied
        if not slug and name:
            cleaned["slug"] = slugify(name)

        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # slug is auto-generated from name; display_order has a model
        # default. Allow leaving both blank.
        self.fields["slug"].required = False
        self.fields["display_order"].required = False
