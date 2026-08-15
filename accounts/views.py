from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


@login_required
def logout_view(request):
    """Log out the current user and return to the login page."""
    logout(request)
    return redirect("/accounts/login/")
