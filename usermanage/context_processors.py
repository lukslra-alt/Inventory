"""Template context processors for the usermanage app."""

from .roles import can_access_pricelist


def pricelist_access(request):
    """Expose the pricelist permission to every template."""
    return {
        "can_access_pricelist": can_access_pricelist(request.user),
    }
