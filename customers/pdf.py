from io import BytesIO
from datetime import date
from pathlib import Path

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from customers.models import Invoice, Customer


def _logo_path():
    """Locate the logo image, falling back to a setting or media dir."""
    candidates = []
    configured = getattr(settings, "LOGO_PATH", "")
    if configured:
        candidates.append(Path(configured))
    candidates.append(Path(settings.MEDIA_ROOT) / "logo.png")
    candidates.append(Path(settings.MEDIA_ROOT) / "logo.jpg")
    candidates.append(Path(settings.BASE_DIR) / "static" / "logo.png")
    candidates.append(Path(settings.BASE_DIR) / "static" / "logo.jpg")
    candidates.append(Path(settings.BASE_DIR) / "static" / "logo.jpeg")

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _money(value):
    """Format a number with commas and two decimal places."""
    try:
        return f"{float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _quantity(value):
    """Format quantity without .00 when it is a whole number."""
    try:
        value = float(value or 0)

        if value.is_integer():
            return str(int(value))

        return f"{value:,.2f}"
    except (TypeError, ValueError):
        return "0"


def invoice_pdf(invoice_number):
    """
    Build an invoice PDF as bytes for the given invoice number.
    """
    invoice = (
        Invoice.objects
        .prefetch_related("items")
        .select_related("customer")
        .get(invoice_number=invoice_number)
    )

    # =========================================================
    # STYLES
    # =========================================================

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="InvoiceTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
        )
    )

    styles.add(
        ParagraphStyle(
            name="NormalText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BoldText",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CustomerName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableHeaderLeft",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableHeaderRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            alignment=TA_RIGHT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ItemText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
        )
    )

    styles.add(
        ParagraphStyle(
            name="NumberText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_RIGHT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TotalLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_RIGHT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TotalAmount",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_RIGHT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="FooterText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.grey,
        )
    )

    # =========================================================
    # DOCUMENT
    # =========================================================

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Invoice {invoice.invoice_number}",
    )

    story = []

    page_width = A4[0] - doc.leftMargin - doc.rightMargin

    # =========================================================
    # HEADER
    # =========================================================

    date_text = (
        invoice.date.strftime("%d/%m/%Y")
        if invoice.date
        else "-"
    )

    logo = None
    logo_path = _logo_path()
    if logo_path:
        logo = Image(
            logo_path,
            width=page_width,
            height=page_width * (325.0 / 1152.0),
        )

    logo_cell = []
    if logo:
        logo_cell.append(logo)
        logo_cell.append(Spacer(1, 4 * mm))

    logo_cell.extend([
        Paragraph(
            f"<b>Date :</b> {date_text}",
            styles["NormalText"],
        ),

        Spacer(1, 2 * mm),

        Paragraph(
            f"<b>Invoice No :</b> {invoice.invoice_number}",
            styles["NormalText"],
        ),
    ])

    header_table = Table(
        [
            [
                logo_cell,
            ]
        ],
        colWidths=[
            page_width,
        ],
    )

    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),

                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),

                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(header_table)

    # =========================================================
    # BILL TO
    # =========================================================

    story.append(Spacer(1, 12 * mm))

    customer_name = (
        invoice.customer.name
        if invoice.customer
        else "-"
    )

    bill_to_table = Table(
        [
            [
                Paragraph(
                    "Bill To",
                    styles["BoldText"],
                )
            ],
            [
                Paragraph(
                    customer_name,
                    styles["CustomerName"],
                )
            ],
        ],
        colWidths=[page_width],
    )

    bill_to_table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),

                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    story.append(bill_to_table)

    story.append(Spacer(1, 10 * mm))

    # =========================================================
    # ITEM TABLE
    # =========================================================

    rows = [
        [
            Paragraph(
                "Quantity",
                styles["TableHeaderLeft"],
            ),

            Paragraph(
                "Description",
                styles["TableHeaderLeft"],
            ),

            Paragraph(
                "Unit Price",
                styles["TableHeaderRight"],
            ),

            Paragraph(
                "Amount",
                styles["TableHeaderRight"],
            ),
        ]
    ]

    for item in invoice.items.all():

        rows.append(
            [
                Paragraph(
                    _quantity(item.qty),
                    styles["ItemText"],
                ),

                Paragraph(
                    item.description or "-",
                    styles["ItemText"],
                ),

                Paragraph(
                    _money(item.sales_price),
                    styles["NumberText"],
                ),

                Paragraph(
                    _money(item.amount),
                    styles["NumberText"],
                ),
            ]
        )

    # Widths must fit inside the printable A4 area.
    item_table = Table(
        rows,
        colWidths=[
            24 * mm,   # Quantity
            97 * mm,   # Description
            30 * mm,   # Unit Price
            30 * mm,   # Amount
        ],
        repeatRows=1,
    )

    item_table.setStyle(
        TableStyle(
            [
                # Header bottom line
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    0.7,
                    colors.black,
                ),

                # Vertical alignment
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),

                # Padding
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    3,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    4,
                ),

                (
                    "TOPPADDING",
                    (0, 1),
                    (-1, -1),
                    4,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 1),
                    (-1, -1),
                    4,
                ),

                # Remove extra padding at left
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),

                # Number columns aligned right
                (
                    "ALIGN",
                    (2, 0),
                    (-1, -1),
                    "RIGHT",
                ),
            ]
        )
    )

    story.append(item_table)

    # =========================================================
    # TOTAL
    # =========================================================

    story.append(Spacer(1, 7 * mm))

    total_table = Table(
        [
            [
                Paragraph(
                    "TOTAL",
                    styles["TotalLabel"],
                ),

                Paragraph(
                    f"LKR {_money(invoice.total)}",
                    styles["TotalAmount"],
                ),
            ]
        ],
        colWidths=[
            page_width - 50 * mm,
            50 * mm,
        ],
    )

    total_table.setStyle(
        TableStyle(
            [
                (
                    "LINEABOVE",
                    (0, 0),
                    (-1, 0),
                    0.8,
                    colors.black,
                ),

                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    0.8,
                    colors.black,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    story.append(total_table)

    # =========================================================
    # FOOTER
    # =========================================================

    story.append(Spacer(1, 15 * mm))

    story.append(
        Paragraph(
            "In case of any mismatch, contact us and report within 3 days.",
            styles["FooterText"],
        )
    )

    # =========================================================
    # BUILD PDF
    # =========================================================

    doc.build(story)

    return buffer.getvalue()


def outstanding_summary_pdf():
    """
    Build a customer outstanding summary PDF as bytes.
    Lists all customers with a positive balance, sorted by highest outstanding.
    """
    customers = (
        Customer.objects
        .filter(balance__gt=0)
        .order_by("-balance")
    )

    total_outstanding = sum(c.balance for c in customers)

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="SummaryTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SummaryDate",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.grey,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableHeaderLeft",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableHeaderRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CustomerText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="MoneyText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TotalLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_RIGHT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TotalAmount",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_RIGHT,
        )
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Customer Outstanding Summary",
    )

    story = []
    page_width = A4[0] - doc.leftMargin - doc.rightMargin

    story.append(
        Paragraph("Customer Outstanding Summary", styles["SummaryTitle"])
    )

    story.append(
        Paragraph(
            f"Generated: {date.today().strftime('%d/%m/%Y')}",
            styles["SummaryDate"],
        )
    )

    story.append(Spacer(1, 8 * mm))

    rows = [
        [
            Paragraph("#", styles["TableHeaderLeft"]),
            Paragraph("Customer", styles["TableHeaderLeft"]),
            Paragraph("Balance (LKR)", styles["TableHeaderRight"]),
        ]
    ]

    for i, customer in enumerate(customers, 1):
        rows.append(
            [
                Paragraph(str(i), styles["CustomerText"]),
                Paragraph(customer.name, styles["CustomerText"]),
                Paragraph(_money(customer.balance), styles["MoneyText"]),
            ]
        )

    summary_table = Table(
        rows,
        colWidths=[
            12 * mm,
            page_width - 52 * mm,
            40 * mm,
        ],
        repeatRows=1,
    )

    summary_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.2)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, 0), 3),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ]
        )
    )

    story.append(summary_table)

    story.append(Spacer(1, 7 * mm))

    total_table = Table(
        [
            [
                Paragraph("TOTAL OUTSTANDING", styles["TotalLabel"]),
                Paragraph(
                    f"LKR {_money(total_outstanding)}",
                    styles["TotalAmount"],
                ),
            ]
        ],
        colWidths=[page_width - 50 * mm, 50 * mm],
    )

    total_table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(total_table)

    doc.build(story)

    return buffer.getvalue()
