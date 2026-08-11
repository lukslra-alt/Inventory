from .roles import can_access_pricelist


def pricelist_access(request):
    return {
        "can_access_pricelist": can_access_pricelist(request.user),
    }
