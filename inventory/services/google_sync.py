"""
Inventory sync orchestration: download/receive a source file, parse it and
sync products.

The flow records each run in SyncHistory and stores the last source hash
in SyncSetting so unchanged sheets are skipped.
"""

import hashlib
import os

from django.utils import timezone

from inventory.services.google_client import download_inventory_csv
from inventory.services.inventory_parser import parse_inventory_file
from inventory.services.sync_engine import sync_products
from inventory.models import SyncHistory, SyncSetting


def _get_setting():
    """Return the single SyncSetting row, creating it if missing."""
    setting = SyncSetting.objects.first()
    if setting is None:
        setting = SyncSetting.objects.create()
    return setting


def _file_hash(filepath):
    digest = hashlib.sha256()
    with open(filepath, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _skipped_result():
    return {
        "skipped": True,
        "added": 0,
        "updated": 0,
        "restored": 0,
        "removed": 0,
        "total_products": 0,
    }


def sync_inventory_from_file(filepath, file_hash=None, force=False):
    """
    Parse and sync a local inventory source file.

    Returns a dict of counts (added/updated/restored/removed). Raises on
    failure, leaving a FAILED SyncHistory row behind.
    """
    setting = _get_setting()
    file_hash = file_hash or _file_hash(filepath)

    if not force and setting.sheet_hash == file_hash:
        SyncHistory.objects.create(
            status="SKIPPED",
            message="Inventory sheet unchanged - no sync needed.",
        )
        return _skipped_result()

    try:
        products = parse_inventory_file(filepath)
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
            message=f"Processed {result['total_products']} products",
        )

        result["skipped"] = False
        return result

    except Exception as error:
        SyncHistory.objects.create(
            status="FAILED",
            message=str(error),
        )
        raise


def sync_inventory():
    """
    Download the inventory source and sync products into the database.

    The downloaded file is always cleaned up, even when parsing fails.
    """
    download = download_inventory_csv()

    if not download["success"]:
        SyncHistory.objects.create(
            status="FAILED",
            message=download["error"],
        )
        raise Exception(download["error"])

    filepath = download["filepath"]

    try:
        return sync_inventory_from_file(
            filepath,
            file_hash=download["hash"],
        )
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
