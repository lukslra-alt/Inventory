"""
Small helper for downloading the source CSVs from Google Drive.

The files are exported from Google Drive by file id, stored in a temp
folder, and returned along with a SHA-256 hash so callers can skip
unchanged sheets.
"""

import hashlib
import os
import requests
from datetime import datetime

from django.conf import settings


# File ids of the shared export sheets on Google Drive.
# Customers: COMP0004_BillsReceivable in the COMP0004 folder.
CUSTOMER_FILE_ID = "1ojyVRpHhFGOsBKpoFyjv-eHPvB71LDnH7BMQMxWgUNU"

INVENTORY_FILE_ID = "175q7kE9L1c0HNqrkMfZ7cP0OqK4ySP-SB6PmFz-xtj4"

# The customer source is a native Google Sheet, so use the Sheets CSV
# export endpoint instead of the Drive download endpoint.
CUSTOMER_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{CUSTOMER_FILE_ID}"
    "/export?format=csv"
)

# The inventory source is a native Google Sheet. Export its first tab as
# CSV; the stock ageing layout is detected by the parser.
INVENTORY_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{INVENTORY_FILE_ID}"
    "/export?format=csv"
)

TEMP_FOLDER = os.path.join(settings.BASE_DIR, "temp")


def _download(url, prefix, extension):
    """
    Download the file at `url` into the temp folder.

    Returns {"success": True, "filepath", "size", "hash"} on success, or
    {"success": False, "error"} when the request fails.
    """
    os.makedirs(TEMP_FOLDER, exist_ok=True)

    # Timestamped filename keeps concurrent runs from colliding.
    filename = (
        f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
    )

    filepath = os.path.join(TEMP_FOLDER, filename)

    try:
        response = requests.get(url, timeout=30)

        # Google returns a sign-in page instead of CSV when a shared sheet
        # is not public. Fail early with a useful message rather than
        # saving HTML as a CSV and confusing the parser.
        content_type = response.headers.get("content-type", "").lower()
        if extension == "csv" and (
            "text/html" in content_type
            or response.content.lstrip()[:15].lower() == b"<!doctype html"
        ):
            return {
                "success": False,
                "error": (
                    "Google Sheet is not publicly accessible. "
                    "Share it with 'Anyone with the link' as a viewer."
                ),
            }

        response.raise_for_status()

        with open(filepath, "wb") as file:
            file.write(response.content)

        return {
            "success": True,
            "filepath": filepath,
            "size": len(response.content),
            "hash": hashlib.sha256(response.content).hexdigest(),
        }

    except requests.RequestException as error:

        return {
            "success": False,
            "error": str(error),
        }


def download_customer_csv():
    """Download and return the customer/bills receivable CSV."""
    return _download(CUSTOMER_CSV_URL, "customers", "csv")


def download_inventory_csv():
    """Download and return the QuickBooks inventory CSV."""
    return _download(INVENTORY_CSV_URL, "inventory", "csv")
