import warnings

import pandas as pd


class QuickBooksParser:

    # Excel columns:
    # C = 2
    # E = 4
    # G = 6
    # K = 10

    ITEM_COLUMN = 2
    DESCRIPTION_COLUMN = 4
    COST_COLUMN = 6
    QTY_COLUMN = 10

    def __init__(self, filepath):
        self.filepath = filepath

    def parse(self):

        # openpyxl warns about defined names referencing sheets that no
        # longer exist in the exported workbook. Harmless — ignore it.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Defined names for sheet index",
                category=UserWarning,
            )

            df = pd.read_excel(
                self.filepath,
                sheet_name="Sheet1",
                header=None
            )

        products = []

        for _, row in df.iterrows():

            # =========================================
            # ITEM
            # =========================================

            item_path = self._text(
                row.iloc[self.ITEM_COLUMN]
            )

            if not item_path:
                continue

            if item_path.lower() == "item":
                continue

            # =========================================
            # DESCRIPTION
            # =========================================

            description = self._text(
                row.iloc[self.DESCRIPTION_COLUMN]
            )

            if not description:
                continue

            # =========================================
            # HIERARCHY
            # =========================================

            parts = [
                part.strip()
                for part in item_path.split(":")
                if part.strip()
            ]

            if not parts:
                continue

            category = parts[0]

            subcategory = (
                parts[1]
                if len(parts) >= 2
                else ""
            )

            level3 = (
                parts[2]
                if len(parts) >= 3
                else ""
            )

            level4 = (
                parts[3]
                if len(parts) >= 4
                else ""
            )

            # =========================================
            # COST FROM EXCEL COLUMN G
            # =========================================

            cost_value = self._number(
                row.iloc[self.COST_COLUMN]
            )

            # =========================================
            # QUANTITY
            # =========================================

            qty_value = self._number(
                row.iloc[self.QTY_COLUMN]
            )

            # =========================================
            # PRODUCT
            # =========================================

            products.append({

                "item": item_path,

                "product_name": description,

                "category": category,

                "subcategory": subcategory,

                "level3": level3,

                "level4": level4,

                "hierarchy_path": item_path,

                "qty": qty_value,

                "cost": cost_value,
            })

        return products

    @staticmethod
    def _text(value):

        if pd.isna(value):
            return ""

        return str(value).strip()

    @staticmethod
    def _number(value):

        if pd.isna(value):
            return 0.0

        # Already numeric
        if isinstance(value, (int, float)):
            return float(value)

        # Handle text such as:
        # "1,250.50"
        # "Rs. 1,250.50"
        # "$1,250.50"

        value = str(value).strip()

        value = (
            value
            .replace(",", "")
            .replace("Rs.", "")
            .replace("Rs", "")
            .replace("$", "")
            .strip()
        )

        number = pd.to_numeric(
            value,
            errors="coerce"
        )

        if pd.isna(number):
            return 0.0

        return float(number)