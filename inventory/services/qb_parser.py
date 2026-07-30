import pandas as pd


class QuickBooksParser:

    PRODUCT_COLUMNS = [2, 3, 4, 5, 6]

    QTY_COLUMN = 7

    AVG_COST_COLUMN = 9

    def __init__(self, filepath):

        self.filepath = filepath

        self.current_category = ""

        self.current_subcategory = ""

        self.current_level3 = ""

        self.current_level4 = ""

    def parse(self):

        df = pd.read_excel(

            self.filepath,

            sheet_name="Sheet1",

            header=None

        )

        products = []

        for _, row in df.iterrows():

            qty = row[self.QTY_COLUMN]

            avg_cost = row[self.AVG_COST_COLUMN]

            # -------------------------
            # HEADING ROW
            # -------------------------

            if pd.isna(pd.to_numeric(qty, errors="coerce")):

                self._update_hierarchy(row)

                continue

            product_name = self._get_product_name(row)

            if not product_name:

                continue

            if product_name.lower().startswith("total"):

                continue

            products.append({

                "product_name": product_name,

                "category": self.current_category,

                "subcategory": self.current_subcategory,

                "level3": self.current_level3,

                "level4": self.current_level4,

                "qty": float(qty),

                "avg_cost": float(pd.to_numeric(avg_cost, errors="coerce") or 0)

            })

        return products

    def _update_hierarchy(self, row):

        c = self._text(row[2])

        d = self._text(row[3])

        e = self._text(row[4])

        f = self._text(row[5])

        if c:

            self.current_category = c

            self.current_subcategory = ""

            self.current_level3 = ""

            self.current_level4 = ""

            return

        if d:

            self.current_subcategory = d

            self.current_level3 = ""

            self.current_level4 = ""

            return

        if e:

            self.current_level3 = e

            self.current_level4 = ""

            return

        if f:

            self.current_level4 = f

            return

    def _get_product_name(self, row):

        for col in [6, 5, 4, 3, 2]:

            value = self._text(row[col])

            if value:

                return value

        return ""

    @staticmethod
    def _text(value):

        if pd.isna(value):

            return ""

        return str(value).strip()