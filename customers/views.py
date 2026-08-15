import calendar
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Min
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from customers.models import Customer, Invoice
from customers.pdf import invoice_pdf


def _months_ago(months):
    """Return today's date shifted back by the given number of months."""
    today = timezone.now().date()
    month = today.month - months
    year = today.year
    if month <= 0:
        month += 12
        year -= 1
    # Clamp the day in case the target month is shorter than today's day.
    day = min(today.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@login_required
def customer_list(request):
    """Paginated customer directory with invoice counts and due status."""
    cutoff_3 = _months_ago(3)
    cutoff_6 = _months_ago(6)

    customers = (
        Customer.objects.annotate(
            invoice_count=Count("invoices"),
            oldest_invoice=Min("invoices__date"),
        )
        .order_by("name")
    )

    # Label customers based on how old their oldest invoice is.
    for customer in customers:
        if customer.oldest_invoice and customer.oldest_invoice < cutoff_6:
            customer.due_status = "overdue"
        elif customer.oldest_invoice and customer.oldest_invoice < cutoff_3:
            customer.due_status = "due"
        else:
            customer.due_status = ""

    paginator = Paginator(customers, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "customers/customer_list.html",
        {"page_obj": page_obj},
    )


@login_required
def customer_detail(request, pk):
    """Detail page showing a customer and their invoices, oldest first."""
    customer = get_object_or_404(Customer, pk=pk)
    invoices = customer.invoices.prefetch_related("items").order_by("date")

    return render(
        request,
        "customers/customer_detail.html",
        {"customer": customer, "invoices": invoices},
    )


@login_required
def invoice_view(request, invoice_number):
    """HTML detail page for a single invoice."""
    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("items", "customer"),
        invoice_number=invoice_number,
    )

    return render(
        request,
        "customers/invoice_detail.html",
        {"invoice": invoice},
    )


@login_required
def invoice_pdf_view(request, invoice_number):
    """Stream a rendered invoice PDF for inline browser display."""
    get_object_or_404(Invoice, invoice_number=invoice_number)

    pdf = invoice_pdf(invoice_number)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="invoice-{invoice_number}.pdf"'
    )
    return response
