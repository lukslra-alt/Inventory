from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from customers.models import Customer, Invoice
from customers.pdf import invoice_pdf


@login_required
def customer_list(request):
    customers = Customer.objects.annotate(
        invoice_count=Count("invoices")
    ).order_by("name")

    paginator = Paginator(customers, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "customers/customer_list.html",
        {"page_obj": page_obj},
    )


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    invoices = customer.invoices.prefetch_related("items").order_by("date")

    return render(
        request,
        "customers/customer_detail.html",
        {"customer": customer, "invoices": invoices},
    )


@login_required
def invoice_view(request, invoice_number):
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
    get_object_or_404(Invoice, invoice_number=invoice_number)

    pdf = invoice_pdf(invoice_number)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="invoice-{invoice_number}.pdf"'
    )
    return response
