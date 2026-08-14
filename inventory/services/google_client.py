import hashlib
import os
import requests
from datetime import datetime

from django.conf import settings


CUSTOMER_FILE_ID = "1h5FRhHggQuR4yGCSAN8C175YXhJ71_cR"

INVENTORY_FILE_ID = "10tJtiUUP96gAYDICu34FCZpQWyIh4l0K"

CUSTOMER_CSV_URL = (
    f"https://drive.google.com/uc?export=download&id={CUSTOMER_FILE_ID}"
)

INVENTORY_CSV_URL = (
    f"https://drive.google.com/uc?export=download&id={INVENTORY_FILE_ID}"
)

TEMP_FOLDER = os.path.join(settings.BASE_DIR, "temp")


def _download(url, prefix, extension):
    os.makedirs(TEMP_FOLDER, exist_ok=True)

    filename = (
        f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
    )

    filepath = os.path.join(TEMP_FOLDER, filename)

    try:
        response = requests.get(url, timeout=30)
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
    return _download(CUSTOMER_CSV_URL, "customers", "csv")


def download_inventory_csv():
    return _download(INVENTORY_CSV_URL, "inventory", "csv")
