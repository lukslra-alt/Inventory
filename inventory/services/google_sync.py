import os

from inventory.services.google_client import download_google_sheet
from inventory.services.qb_parser import QuickBooksParser
from inventory.services.sync_engine import sync_products
from inventory.models import SyncHistory


def sync_inventory():
    # Download Google Sheet

    download = download_google_sheet()

    if not download["success"]:
        SyncHistory.objects.create(
            status="FAILED",
            message=download["error"]
        )

        raise Exception(
            download["error"]
        )

    filepath = download["filepath"]

    try:

        # Parse Excel

        parser = QuickBooksParser(
            filepath
        )

        products = parser.parse()

        # Sync database

        result = sync_products(
            products
        )

        # Save history

        SyncHistory.objects.create(

            added_count=result["added"],

            updated_count=result["updated"],

            restored_count=result["restored"],

            removed_count=result["removed"],

            status="SUCCESS",

            message=(
                f"Processed "
                f"{result['total_products']} products"
            )

        )

        return result



    except Exception as error:

        SyncHistory.objects.create(

            status="FAILED",

            message=str(error)

        )

        raise



    finally:

        # Remove temporary file

        if os.path.exists(filepath):
            os.remove(filepath)
