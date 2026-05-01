import json
import os
from apify_client import ApifyClient
from config import API_KEYS_FILE


def muat_api_keys() -> list[str]:
    """Membaca API keys dari api_keys.json. Mengabaikan placeholder."""
    if not os.path.isfile(API_KEYS_FILE):
        return []
    with open(API_KEYS_FILE, 'r') as f:
        data = json.load(f)
    return [k for k in data.get('api_keys', []) if k and 'yourKey' not in k]


def simpan_api_keys(keys: list[str]) -> None:
    """Menyimpan daftar API keys kembali ke api_keys.json."""
    with open(API_KEYS_FILE, 'w') as f:
        json.dump({'api_keys': keys}, f, indent=2)


class ApiKeyManager:
    """Mengelola kumpulan API key Apify dengan rotasi otomatis."""

    def __init__(self, keys: list[str]):
        self.keys          = list(keys)
        self.current_index = 0
        self.exhausted     = set()

    def get_client(self) -> ApifyClient:
        return ApifyClient(self.keys[self.current_index])

    def status(self) -> str:
        sisa = len(self.keys) - len(self.exhausted)
        return f"Key #{self.current_index + 1} aktif | Sisa: {sisa}/{len(self.keys)}"

    def rotate(self) -> bool:
        """Tandai key saat ini habis, beralih ke key berikutnya. Return False jika semua habis."""
        self.exhausted.add(self.current_index)
        for i in range(len(self.keys)):
            if i not in self.exhausted:
                self.current_index = i
                print(f"🔄 ROTASI KEY → Key #{i + 1} (...{self.keys[i][-8:]})")
                return True
        return False

    def tambah_key(self, key: str) -> None:
        """Tambah key baru, simpan ke file, dan jadikan aktif."""
        self.keys.append(key)
        simpan_api_keys(self.keys)
        self.current_index = len(self.keys) - 1
        print(f"✅ Key baru ditambahkan sebagai Key #{len(self.keys)}")

    def semua_habis(self) -> bool:
        return len(self.exhausted) >= len(self.keys)
