from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Min
from django.shortcuts import get_object_or_404, render

from customers.models import Customer


@login_required
def customer_list(request):
    """Paginated customer directory with invoice counts and due status."""
    customers = (
        Customer.objects.annotate(
            invoice_count=Count("invoices"),
            oldest_invoice=Min("invoices__date"),
        )
        .order_by("name")
    )

    # The due_status property classifies each customer from the
    # oldest_invoice annotation computed above.
    paginator = Paginator(customers, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Pagination links with ellipses instead of every page number.
    page_range = page_obj.paginator.get_elided_page_range(page_obj.number)

    return render(
        request,
        "customers/customer_list.html",
        {
            "page_obj": page_obj,
            "page_range": page_range,
        },
    )


@login_required
def customer_detail(request, pk):
    """Detail page showing a customer and their invoices, oldest first."""
    customer = get_object_or_404(Customer, pk=pk)
    invoices = customer.invoices.order_by("date")

    return render(
        request,
        "customers/customer_detail.html",
        {"customer": customer, "invoices": invoices},
    )

