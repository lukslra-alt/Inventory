"""PDF generation for price list pages (reportlab newspaper layout)."""

import math
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

COMPANY_NAME = "Waseer Trading Dambulla"


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


def price_page_pdf_bytes(page, cols):
    """Build a printable PDF price list for a page, in 1-3 newspaper columns."""
    entries = _page_entries(page)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=COMPANY_NAME,
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

    today = datetime.now().strftime('%d-%m-%Y')

    story = []

    header = Table(
        [[Paragraph(today, date_style),
          Paragraph(COMPANY_NAME, company_style),
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

    return pdf