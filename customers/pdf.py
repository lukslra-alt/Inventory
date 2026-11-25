from io import BytesIO
from datetime import date

from django.db.models import Sum

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from customers.models import Customer


def _money(value):
    """Format a number with commas and two decimal places."""
    try:
        return f"{float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


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

    total_outstanding = (
        customers.aggregate(total=Sum("balance"))["total"]
        or 0
    )

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
