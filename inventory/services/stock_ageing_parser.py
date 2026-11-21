"""Parser for Tally-style Stock Ageing Analysis exports (XLSX or CSV)."""

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN

import openpyxl


class StockAgeingParser:
    """
    Parse a Stock Ageing Analysis export into product dictionaries.

    Layout (header row is detected, not fixed):

        Item Details | Closing Qty | Unit |
        (0-30) Qty | Value | (31-60) Qty | Value | ... | (>=151) Qty | Value

    The report has no item path and no explicit cost column. Unit cost is
    derived as total ageing value / closing quantity. When the report has
    no value for an item, ``cost`` is returned as None so the sync engine
    preserves the cost already stored in the database.
    """

    VALUE_COLUMNS = (4, 6, 8, 10, 12, 14)

    def __init__(self, filepath):
        self.filepath = filepath

    @classmethod
    def is_stock_ageing_file(cls, filepath):
        """Return True when the file has the Stock Ageing header."""
        if not str(filepath).lower().endswith((".xlsx", ".xlsm", ".csv")):
            return False

        parser = cls(filepath)
        rows = parser._read_rows(limit=20)
        return any(parser._is_header(row) for row in rows)

    def parse(self):
        rows = self._read_rows()
        products = []
        header_seen = False

        for row in rows:
            cells = list(row) + [None] * (15 - len(row))

            if not header_seen:
                header_seen = self._is_header(cells)
                continue

            name = self._text(cells[0])
            if not name or name.lower() == "item details":
                continue

            # The report footer starts with a blank item cell, but some
            # exports use "Totals" in the Unit column instead.
            if self._text(cells[2]).lower() == "totals":
                break

            qty = max(self._number(cells[1]), Decimal("0.00")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_EVEN,
            )
            total_value = sum(
                (self._number(cells[index]) for index in self.VALUE_COLUMNS),
                Decimal("0.00"),
            )

            if qty > 0 and total_value > 0:
                # Match the two-decimal DecimalField so repeated syncs do
                # not report phantom updates on rounding differences.
                cost = (total_value / qty).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_EVEN,
                )
            else:
                # Keep the stored cost when this report has no value.
                cost = None

            products.append({
                "item": name,
                "product_name": name,
                "category": "",
                "subcategory": "",
                "level3": "",
                "level4": "",
                "hierarchy_path": "",
                "qty": qty,
                "cost": cost,
                # The report uses names, not QuickBooks item paths.
                "match_by": "product_name",
                "preserve_identity": True,
                # Ageing lists only items holding stock. Absent items
                # must stay active with zero quantity, not be deleted.
                "deactivate_missing": False,
            })

        if not header_seen:
            raise ValueError(
                "Stock Ageing Analysis header (Item Details / Closing Qty) "
                "was not found."
            )

        return products

    def _is_header(self, row):
        if len(row) < 2:
            return False
        return (
            self._text(row[0]).lower() == "item details"
            and self._text(row[1]).lower() == "closing qty"
        )

    def _read_rows(self, limit=None):
        if str(self.filepath).lower().endswith(".csv"):
            return self._read_csv(limit)
        return self._read_excel(limit)

    def _read_csv(self, limit):
        rows = []
        with open(
            self.filepath,
            newline="",
            encoding="utf-8-sig",
        ) as handle:
            for index, row in enumerate(csv.reader(handle)):
                if limit is not None and index >= limit:
                    break
                rows.append(row)
        return rows

    def _read_excel(self, limit):
        workbook = openpyxl.load_workbook(
            self.filepath,
            read_only=True,
            data_only=True,
        )
        rows = []
        try:
            iterator = workbook.active.iter_rows(values_only=True)
            for index, row in enumerate(iterator):
                if limit is not None and index >= limit:
                    break
                rows.append(row)
        finally:
            workbook.close()
        return rows

    @staticmethod
    def _text(value):
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _number(value):
        if value is None:
            return Decimal("0.00")
        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value))
        cleaned = (
            str(value)
            .strip()
            .replace(",", "")
            .replace("Rs.", "")
            .replace("Rs", "")
            .replace("$", "")
            .strip()
        )
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return Decimal("0.00")
