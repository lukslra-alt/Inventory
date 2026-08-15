from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import UserProfile
from .roles import ROLE_CHOICES, ROLE_STAFF, role_of, role_to_flags


def save_pricelist_access(form, user):
    """Persist the form's pricelist-access checkbox to the user's profile."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.can_access_pricelist = form.cleaned_data["pricelist_access"]
    profile.save()


class PricelistAccessField(forms.BooleanField):
    """Boolean field with sensible defaults for the pricelist checkbox."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", "Pricelist access")
        kwargs.setdefault(
            "help_text",
            "Allow this user to view the price list. Always enabled for staff.",
        )
        kwargs.setdefault("required", False)
        kwargs.setdefault(
            "widget", forms.CheckboxInput(attrs={"class": "form-check-input"})
        )
        super().__init__(*args, **kwargs)


class UserCreateForm(forms.ModelForm):
    """Create a User, hashing the password and applying the chosen role."""
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Password"}
        ),
        required=True,
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial=ROLE_STAFF,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    pricelist_access = PricelistAccessField()

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Username"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "First name"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Last name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Email"}
            ),
        }

    def clean_password(self):
        # Reuse Django's built-in password validators.
        password = self.cleaned_data.get("password")
        validate_password(password)
        return password

    def save(self, commit=True):
        # Hash the password and translate the selected role into flags.
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        flags = role_to_flags(self.cleaned_data["role"])
        user.is_staff = flags["is_staff"]
        user.is_superuser = flags["is_superuser"]
        user.is_active = True
        if commit:
            user.save()
            save_pricelist_access(self, user)
        return user


class UserEditForm(forms.ModelForm):
    """Edit an existing user, syncing role selection with the User flags."""
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    pricelist_access = PricelistAccessField()

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, **kwargs):
        # Pre-fill the role and pricelist fields from the existing user.
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["role"].initial = role_of(self.instance)
            profile = UserProfile.objects.filter(user=self.instance).first()
            self.fields["pricelist_access"].initial = bool(
                profile and profile.can_access_pricelist
            )

    def save(self, commit=True):
        # Keep the role selection in sync with the User's staff flags.
        user = super().save(commit=False)
        flags = role_to_flags(self.cleaned_data["role"])
        user.is_staff = flags["is_staff"]
        user.is_superuser = flags["is_superuser"]
        if commit:
            user.save()
            save_pricelist_access(self, user)
        return user


class PasswordResetForm(forms.Form):
    """Plain form capturing a validated replacement password."""
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "New password"}
        ),
        required=True,
    )

    def clean_password(self):
        # Validate the new password with Django's password validators.
        password = self.cleaned_data.get("password")
        validate_password(password)
        return password
