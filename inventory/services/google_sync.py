"""
Inventory sync orchestration: download the sheet, parse it, sync products.

The flow records each run in SyncHistory and stores the last sheet hash
in SyncSetting so unchanged sheets are skipped.
"""

import os

from django.utils import timezone

from inventory.services.google_client import download_inventory_csv
from inventory.services.qb_parser import QuickBooksParser
from inventory.services.sync_engine import sync_products
from inventory.models import SyncHistory, SyncSetting


def _get_setting():
    """Return the single SyncSetting row, creating it if missing."""
    setting = SyncSetting.objects.first()
    if setting is None:
        setting = SyncSetting.objects.create()
    return setting


def sync_inventory():
    """
    Download the inventory CSV and sync products into the database.

    Returns a dict of counts (added/updated/restored/removed). Raises on
    failure, leaving a FAILED SyncHistory row behind. The downloaded file
    is always cleaned up.
    """
    setting = _get_setting()

    download = download_inventory_csv()

    if not download["success"]:
        SyncHistory.objects.create(
            status="FAILED",
            message=download["error"],
        )

        raise Exception(download["error"])

    filepath = download["filepath"]

    try:
        file_hash = download["hash"]

        # Skip parsing entirely when the sheet content has not changed.
        if setting.sheet_hash == file_hash:
            SyncHistory.objects.create(
                status="SKIPPED",
                message="Inventory sheet unchanged - no sync needed.",
            )

            return {
                "skipped": True,
                "added": 0,
                "updated": 0,
                "restored": 0,
                "removed": 0,
                "total_products": 0,
            }

        parser = QuickBooksParser(filepath)

        products = parser.parse()

        result = sync_products(products)

        # Record the new hash and summary counts on the setting row.
        setting.sheet_hash = file_hash
        setting.last_sync = timezone.now()
        setting.total_products = result["total_products"]
        setting.added = result["added"]
        setting.updated = result["updated"]
        setting.restored = result["restored"]
        setting.removed = result["removed"]
        setting.save()

        SyncHistory.objects.create(
            added_count=result["added"],
            updated_count=result["updated"],
            restored_count=result["restored"],
            removed_count=result["removed"],
            status="SUCCESS",
            message=(
                f"Processed "
                f"{result['total_products']} products"
            ),
        )

        result["skipped"] = False

        return result

    except Exception as error:
        SyncHistory.objects.create(
            status="FAILED",
            message=str(error),
        )

        raise

    finally:
        # Always remove the temporary CSV, even on failure.
        if os.path.exists(filepath):
            os.remove(filepath)
