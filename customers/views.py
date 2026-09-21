import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Min, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from customers.models import Customer, Invoice
from customers.pdf import invoice_pdf, outstanding_summary_pdf


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

    # Build outstanding summary for WhatsApp share (all customers, not just page).
    outstanding = list(
        Customer.objects.filter(balance__gt=0)
        .order_by("-balance")
        .values_list("name", "balance")
    )
    total_outstanding = (
        Customer.objects.filter(balance__gt=0)
        .aggregate(total=Sum("balance"))["total"]
        or 0
    )

    return render(
        request,
        "customers/customer_list.html",
        {
            "page_obj": page_obj,
            "page_range": page_range,
            "outstanding_json": json.dumps(
                [[name, str(bal)] for name, bal in outstanding]
            ),
            "total_outstanding": total_outstanding,
        },
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
    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("items").select_related("customer"),
        invoice_number=invoice_number,
    )

    pdf = invoice_pdf(invoice)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="invoice-{invoice_number}.pdf"'
    )
    return response


@login_required
def outstanding_pdf_view(request):
    """Stream the customer outstanding summary as a PDF."""
    pdf = outstanding_summary_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        'inline; filename="outstanding-summary.pdf"'
    )
    return response
