from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .roles import ROLE_CHOICES, ROLE_STAFF, role_of, role_to_flags


class UserCreateForm(forms.ModelForm):
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
        password = self.cleaned_data.get("password")
        validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        flags = role_to_flags(self.cleaned_data["role"])
        user.is_staff = flags["is_staff"]
        user.is_superuser = flags["is_superuser"]
        user.is_active = True
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

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
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["role"].initial = role_of(self.instance)

    def save(self, commit=True):
        user = super().save(commit=False)
        flags = role_to_flags(self.cleaned_data["role"])
        user.is_staff = flags["is_staff"]
        user.is_superuser = flags["is_superuser"]
        if commit:
            user.save()
        return user


class PasswordResetForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "New password"}
        ),
        required=True,
    )

    def clean_password(self):
        password = self.cleaned_data.get("password")
        validate_password(password)
        return password
