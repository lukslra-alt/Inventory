from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect

from .forms import UserCreateForm, UserEditForm, PasswordResetForm
from .models import UserProfile
from .roles import admin_required


@admin_required
def user_list(request):
    users = User.objects.all().order_by("username")
    profile_map = {
        p.user_id: p.can_access_pricelist
        for p in UserProfile.objects.all()
    }
    rows = [
        {
            "user": user,
            "pricelist_access": profile_map.get(user.pk, False),
        }
        for user in users
    ]
    paginator = Paginator(rows, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "usermanage/user_list.html",
        {
            "page_obj": page_obj,
            "total_users": User.objects.count(),
            "staff_users": User.objects.filter(is_staff=True).count(),
            "active_users": User.objects.filter(is_active=True).count(),
        },
    )


@admin_required
def user_add(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" created.')
            return redirect("usermanage:user_list")
    else:
        form = UserCreateForm()

    return render(
        request,
        "usermanage/user_form.html",
        {"form": form, "title": "Add User"},
    )


@admin_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{user.username}" updated.')
            return redirect("usermanage:user_list")
    else:
        form = UserEditForm(instance=user)

    return render(
        request,
        "usermanage/user_form.html",
        {"form": form, "title": f"Edit User: {user.username}", "user": user},
    )


@admin_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect("usermanage:user_list")
    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" deleted.')
        return redirect("usermanage:user_list")
    return render(
        request,
        "usermanage/user_confirm_delete.html",
        {"user": user},
    )


@admin_required
def user_reset_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, f'Password for "{user.username}" reset.')
            return redirect("usermanage:user_list")
    else:
        form = PasswordResetForm()

    return render(
        request,
        "usermanage/password_reset.html",
        {"form": form, "user": user},
    )
