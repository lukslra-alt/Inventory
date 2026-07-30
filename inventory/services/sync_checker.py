from inventory.models import SyncSetting
from .sync_hash import calculate_file_hash


def check_sheet_changed(filepath):
    current_hash = calculate_file_hash(filepath)

    setting, created = SyncSetting.objects.get_or_create(
        id=1
    )

    if setting.sheet_hash == current_hash:
        return {
            "changed": False,
            "hash": current_hash
        }

    return {
        "changed": True,
        "hash": current_hash
    }


def save_sheet_hash(file_hash):
    setting, created = SyncSetting.objects.get_or_create(
        id=1
    )

    setting.sheet_hash = file_hash
    setting.save()
