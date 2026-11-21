"""Format detection for inventory source files."""

from inventory.services.qb_parser import QuickBooksParser
from inventory.services.stock_ageing_parser import StockAgeingParser


def parse_inventory_file(filepath):
    """
    Parse an inventory export, detecting the known source layouts.

    Supported formats:
      - QuickBooks CSV / Excel item export
      - Tally Stock Ageing Analysis Excel export
    """
    if StockAgeingParser.is_stock_ageing_file(filepath):
        return StockAgeingParser(filepath).parse()

    return QuickBooksParser(filepath).parse()
