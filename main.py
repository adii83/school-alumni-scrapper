
from config              import API_KEYS_FILE
from core.api_manager    import muat_api_keys, simpan_api_keys, ApiKeyManager
from modes.mode_excel    import mode_excel
from modes.mode_manual   import mode_manual


def main() -> None:
    print("=" * 60)
    print("🚀 MASS-PROFILING ALUMNI UMM — LinkedIn Scraper")
    print("=" * 60)

    api_keys = muat_api_keys()
    if not api_keys:
        print(f"⚠️  Tidak ada API key valid di '{API_KEYS_FILE}'.")
        manual = input("🔑 Masukkan API Token Apify secara manual: ").strip()
        if not manual:
            print("Token tidak boleh kosong! Program dihentikan.")
            return
        api_keys = [manual]
        simpan_api_keys(api_keys)

    key_mgr = ApiKeyManager(api_keys)
    print(f"✅ {len(api_keys)} API key dimuat. {key_mgr.status()}")

    print("\n" + "─" * 60)
    print("  Pilih Mode Pencarian:")
    print("  [1] 📊 Scraping dari file Excel (Data Alumni.xlsx)")
    print("  [2] ✏️  Pencarian Manual (input nama langsung)")
    print("─" * 60)

    pilihan = input("  Masukkan pilihan (1 / 2): ").strip()

    if pilihan == '1':
        mode_excel(key_mgr)
    elif pilihan == '2':
        mode_manual(key_mgr)
    else:
        print("Pilihan tidak valid. Program dihentikan.")


if __name__ == '__main__':
    main()
