"""
Price list app views: public category browsing plus staff management and PDF.

Public pages are guarded by pricelist_required; management endpoints are
restricted to staff and mostly return small JSON responses consumed by the
management UI's drag-and-drop ordering.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import PricePage, PriceListItem, PriceListHeading
from .forms import PricePageForm, PriceListHeadingForm
from inventory.models import Product
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache

from usermanage.roles import pricelist_required

from io import BytesIO
import math
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)


# Shows all categories
@never_cache
@pricelist_required
def price_categories(request):
    """Landing page listing every price list category."""
    pages = PricePage.objects.all()

    return render(
        request,
        'pricelist/categories.html',
        {
            'pages': pages
        }
    )


# Shows one category page
@never_cache
@pricelist_required
def price_page(request, slug):
    """Render a single price page with its items and headings in order."""
    page = get_object_or_404(
        PricePage.objects.prefetch_related(
            'items__product',
            'headings'
        ),
        slug=slug
    )

    entries = _page_entries(page)

    return render(
        request,
        'pricelist/price_page.html',
        {
            'page': page,
            'entries': entries
        }
    )


@staff_member_required
def add_heading(request, page_id):
    """Add a section heading to a price page."""
    page = get_object_or_404(
        PricePage,
        id=page_id
    )

    if request.method == "POST":
        form = PriceListHeadingForm(request.POST)

        if form.is_valid():
            heading = form.save(commit=False)
            heading.page = page
            heading.save()

            messages.success(
                request,
                f'Heading "{heading.text}" added to {page.name}.'
            )

            return redirect('price_manage')

    else:
        form = PriceListHeadingForm()

    return render(
        request,
        'pricelist/add_heading.html',
        {
            'form': form,
            'page': page,
        }
    )


@login_required
@staff_member_required
def add_products(request, page_id):
    """Search products and attach selected ones to a price page."""
    page = get_object_or_404(
        PricePage,
        id=page_id
    )

    products = []

    search = request.GET.get('search', '')

    if search:
        products = Product.objects.filter(
            product_name__icontains=search
        ).order_by("product_name")

    if request.method == "POST":

        selected_products = request.POST.getlist(
            'products'
        )

        for product_id in selected_products:
            product = Product.objects.get(
                item=product_id
            )

            # get_or_create keeps repeated adds from duplicating entries.
            PriceListItem.objects.get_or_create(
                page=page,
                product=product
            )

        messages.success(
            request,
            f"Added {len(selected_products)} product(s) to {page.name}."
        )

        return redirect(
            'price_manage'
        )

    added_items = set(
        PriceListItem.objects.filter(
            page=page
        ).values_list("product_id", flat=True)
    )

    return render(
        request,
        'pricelist/add_products.html',
        {
            'page': page,
            'products': products,
            'search': search,
            'added_items': added_items,
        }
    )


@staff_member_required
def add_category(request):
    """Create a new price page/category."""
    if request.method == "POST":
        form = PricePageForm(request.POST)

        if form.is_valid():
            page = form.save()
            messages.success(
                request,
                f'Category "{page.name}" created.',
            )
            return redirect("price_manage")

    else:
        form = PricePageForm()

    return render(
        request,
        "pricelist/add_category.html",
        {
            "form": form,
        }
    )


@never_cache
@staff_member_required
def price_manage(request):
    """Management overview of pages with item and visibility totals."""
    pages = PricePage.objects.prefetch_related(
        'items'
    ).annotate(
        total_items=Count('items'),
        visible_items=Count(
            'items',
            filter=Q(items__visible=True)
        ),
    ).order_by('display_order', 'id')

    total_pages = pages.count()
    total_items = sum(p.total_items for p in pages)
    visible_items = sum(p.visible_items for p in pages)

    return render(
        request,
        'pricelist/manage_categories.html',
        {
            'pages': pages,
            'total_pages': total_pages,
            'total_items': total_items,
            'visible_items': visible_items,
        }
    )


def _page_entries(page):
    """
    Returns a list of (display_order, kind, obj) tuples sorted by display_order.
    kind is either "product" (PriceListItem) or "heading" (PriceListHeading).
    """
    entries = []

    for item in page.items.all():
        entries.append(
            (item.display_order, "product", item)
        )

    for heading in page.headings.all():
        entries.append(
            (heading.display_order, "heading", heading)
        )

    entries.sort(key=lambda e: e[0])

    return entries


@staff_member_required
def edit_page(request, page_id):
    """Edit page contents: add products by search and reorder headings/items."""
    page = get_object_or_404(
        PricePage.objects.prefetch_related(
            'items__product',
            'headings'
        ),
        id=page_id
    )

    if request.method == "POST":
        selected_products = request.POST.getlist(
            'products'
        )

        added = 0

        for product_id in selected_products:
            product = Product.objects.filter(
                item=product_id
            ).first()

            if not product:
                continue

            _, created = PriceListItem.objects.get_or_create(
                page=page,
                product=product
            )

            if created:
                added += 1

        messages.success(
            request,
            f"Added {added} product(s) to {page.name}."
        )

        return redirect('edit_page', page_id=page.id)

    search = request.GET.get('search', '')

    results = Product.objects.none()

    if search:
        results = Product.objects.filter(
            product_name__icontains=search
        ).order_by("product_name")

    added_ids = set(
        page.items.values_list("product_id", flat=True)
    )

    return render(
        request,
        'pricelist/edit_page.html',
        {
            'page': page,
            'entries': _page_entries(page),
            'search': search,
            'results': results,
            'added_ids': added_ids,
        }
    )


@staff_member_required
@require_POST
def reorder_page(request, page_id):
    """Persist the new drag-and-drop order of a page's items and headings."""
    page = get_object_or_404(
        PricePage,
        id=page_id
    )

    # POST order entries are encoded as "kind:id", e.g. "product:12".
    order = request.POST.getlist('order')

    for position, entry in enumerate(order, start=1):
        kind, _, obj_id = entry.partition(':')

        if kind == 'product':
            PriceListItem.objects.filter(
                id=obj_id,
                page=page
            ).update(display_order=position)

        elif kind == 'heading':
            PriceListHeading.objects.filter(
                id=obj_id,
                page=page
            ).update(display_order=position)

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def toggle_item(request, page_id):
    """Toggle visibility of an item on a page (used by the manage UI)."""
    kind = request.POST.get('type')
    obj_id = request.POST.get('id')
    visible = request.POST.get('visible') == 'true'

    if kind == 'product':
        PriceListItem.objects.filter(
            id=obj_id,
            page_id=page_id
        ).update(visible=visible)

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def remove_item(request, page_id):
    """Remove an item or heading from a page."""
    kind = request.POST.get('type')
    obj_id = request.POST.get('id')

    if kind == 'product':
        PriceListItem.objects.filter(
            id=obj_id,
            page_id=page_id
        ).delete()

    elif kind == 'heading':
        PriceListHeading.objects.filter(
            id=obj_id,
            page_id=page_id
        ).delete()

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def reorder_categories(request):
    """Persist the new drag-and-drop order of the category pages."""
    order = request.POST.getlist('order')

    for position, page_id in enumerate(order, start=1):
        PricePage.objects.filter(
            id=page_id
        ).update(display_order=position)

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def rename_category(request):
    """Rename a price page/category via the manage UI."""
    page_id = request.POST.get('id')
    name = (request.POST.get('name') or '').strip()

    if not page_id or not name:
        return JsonResponse(
            {'ok': False, 'error': 'Category name is required'}
        )

    page = get_object_or_404(
        PricePage,
        id=page_id
    )

    page.name = name
    page.save()

    return JsonResponse({'ok': True})


@pricelist_required
def price_page_pdf(request, slug):
    """Generate a printable PDF price list for a page, 1-3 newspaper columns."""
    page = get_object_or_404(
        PricePage.objects.prefetch_related(
            'items__product',
            'headings'
        ),
        slug=slug
    )

    entries = _page_entries(page)

    # Column count is user-tunable via ?cols=1|2|3 and clamped safely.
    try:
        cols = max(1, min(int(request.GET.get('cols', 1)), 3))
    except (TypeError, ValueError):
        cols = 1

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title='Waseer Trading Dambulla',
    )

    styles = getSampleStyleSheet()

    date_style = ParagraphStyle(
        'date', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, leading=11,
    )
    company_style = ParagraphStyle(
        'company', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=17, leading=20,
        alignment=TA_CENTER,
    )
    category_style = ParagraphStyle(
        'category', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=14, leading=18,
        spaceBefore=10, spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        'heading', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10, leading=14,
        backColor=colors.HexColor('#f2f2f2'),
        borderPadding=(3, 6, 3, 6),
        spaceBefore=8,
    )
    name_style = ParagraphStyle(
        'name', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10, leading=14,
    )
    price_style = ParagraphStyle(
        'price', parent=name_style,
        fontName='Helvetica-Bold', alignment=TA_RIGHT,
    )

    from datetime import datetime
    today = datetime.now().strftime('%d-%m-%Y')

    story = []

    header = Table(
        [[Paragraph(today, date_style),
          Paragraph('Waseer Trading Dambulla', company_style),
          '']],
        colWidths=[3 * cm, None, 3 * cm],
    )
    header.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.75, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header)

    story.append(Paragraph(page.name, category_style))

    # Items and headings in display order, filling columns newspaper-style.
    item_run = []
    used_width = doc.width

    def flush_item_run():
        nonlocal item_run
        if not item_run:
            return
        n = len(item_run)
        per_col = int(math.ceil(n / cols))
        columns = [
            item_run[i * per_col:(i + 1) * per_col]
            for i in range(cols)
        ]
        rows = []
        for r in range(per_col):
            row_cells = []
            for c in range(cols):
                if r < len(columns[c]):
                    entry = columns[c][r]
                    cell = Table(
                        [[Paragraph(entry[2].product.product_name, name_style),
                          Paragraph(
                              f'Rs. {entry[2].product.sales_price}', price_style)]],
                        colWidths=[used_width / cols - 2.2 * cm, 2.2 * cm],
                    )
                    cell.setStyle(TableStyle([
                        ('LEFTPADDING', (0, 0), (-1, -1), 2),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
                    ]))
                    row_cells.append(cell)
                else:
                    row_cells.append('')
            rows.append(row_cells)
        table = Table(
            rows,
            colWidths=[used_width / cols] * cols,
        )
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(table)
        story.append(Spacer(1, 6))
        item_run = []

    for entry in entries:
        if entry[1] == 'heading':
            flush_item_run()
            story.append(Paragraph(entry[2].text, heading_style))
        elif entry[2].visible:
            item_run.append(entry)

    flush_item_run()

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="pricelist-{page.slug}.pdf"'
    )
    return response
