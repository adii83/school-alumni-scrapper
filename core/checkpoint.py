import json
import os
from config import CHECKPOINT_FILE


def simpan_checkpoint(data: dict) -> None:
    """Simpan progress saat ini ke file checkpoint JSON."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def muat_checkpoint() -> dict | None:
    """Baca checkpoint yang tersimpan. Return None jika tidak ada."""
    if os.path.isfile(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return None


def hapus_checkpoint() -> None:
    """Hapus file checkpoint setelah batch selesai sempurna."""
    if os.path.isfile(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
