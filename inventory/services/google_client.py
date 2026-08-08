import os
import requests
from datetime import datetime

from django.conf import settings


SPREADSHEET_ID = "1ExDKhDUEmDbLYSzGoK07lsDbQgHh5j92"
GID = "1396207375"

GOOGLE_SHEET_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{SPREADSHEET_ID}/export?format=xlsx&gid={GID}"
)

TEMP_FOLDER = os.path.join(settings.BASE_DIR, "temp")


def download_google_sheet():

    os.makedirs(
        TEMP_FOLDER,
        exist_ok=True
    )

    filename = (
        f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )

    filepath = os.path.join(
        TEMP_FOLDER,
        filename
    )

    try:

        response = requests.get(
            GOOGLE_SHEET_URL,
            timeout=30
        )

        response.raise_for_status()

        with open(
            filepath,
            "wb"
        ) as file:

            file.write(
                response.content
            )

        return {
            "success": True,
            "filepath": filepath,
            "size": len(response.content)
        }

    except requests.RequestException as error:

        return {
            "success": False,
            "error": str(error)
        }