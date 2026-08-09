from django.conf import settings
from django.contrib.auth.decorators import user_passes_test


ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"
ROLE_CUSTOMER = "customer"

ROLE_CHOICES = [
    (ROLE_ADMIN, "Admin (full access)"),
    (ROLE_STAFF, "Staff (inventory, pricelist, customers)"),
    (ROLE_CUSTOMER, "Customer (pricelist and customers only)"),
]


def is_admin(user):
    return bool(user.is_authenticated and user.is_superuser)


def is_staff(user):
    return bool(user.is_authenticated and user.is_staff)


def role_of(user):
    if is_admin(user):
        return ROLE_ADMIN
    if is_staff(user):
        return ROLE_STAFF
    return ROLE_CUSTOMER


def role_to_flags(role):
    if role == ROLE_ADMIN:
        return {"is_staff": True, "is_superuser": True}
    if role == ROLE_STAFF:
        return {"is_staff": True, "is_superuser": False}
    return {"is_staff": False, "is_superuser": False}


def admin_required(view_func):
    return user_passes_test(
        lambda u: u.is_active and u.is_superuser,
        login_url=settings.LOGIN_URL,
        redirect_field_name=None,
    )(view_func)
