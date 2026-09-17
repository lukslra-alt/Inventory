import os

from django.conf import settings
from django.http import HttpResponse


def service_worker(request):
    """Serve the PWA service worker from the site root with scope allowed."""
    path = os.path.join(
        settings.BASE_DIR,
        "inventory",
        "static",
        "service-worker.js",
    )

    with open(path, "rb") as handle:
        content = handle.read()

    response = HttpResponse(
        content,
        content_type="application/javascript",
    )

    # Allow the worker (served from the site root) to control "/"
    response["Service-Worker-Allowed"] = "/"

    # iOS Safari aggressively caches HTTP responses. Without these headers it
    # may serve a stale service worker and never see updates.
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    return response
