from core.apify_service import panggil_apify, proses_hasil
from core.api_manager   import ApiKeyManager
from utils.name_utils   import pisahkan_nama


def mode_manual(key_mgr: ApiKeyManager) -> None:
    """Pencarian interaktif satu per satu berdasarkan input nama langsung."""

    print("\n" + "=" * 55)
    print("✏️  MODE MANUAL — Pencarian Langsung by Nama")
    print("=" * 55)
    print("Ketik nama lengkap alumni lalu tekan Enter.")
    print("Ketik 'selesai' atau biarkan kosong untuk keluar.\n")

    file_output = input("💾 Nama file output CSV (contoh: hasil_manual.csv): ").strip()
    if not file_output:
        file_output = "hasil_manual.csv"
    if not file_output.endswith('.csv'):
        file_output += '.csv'

    filter_input = input("🔍 Filter hanya Alumni UMM? (y/n, default y): ").strip().lower()
    filter_umm   = (filter_input != 'n')

    counter = 0

    while True:
        print("\n" + "-" * 55)
        nama_input = input(f"👤 [{counter + 1}] Nama lengkap alumni (atau 'selesai'): ").strip()

        if not nama_input or nama_input.lower() == 'selesai':
            break

        first_name, last_name = pisahkan_nama(nama_input)
        if not first_name:
            print("⚠️  Nama tidak valid, coba lagi.")
            continue

        print("   (Tekan Enter untuk melewati field berikut)")
        nim_asli  = input("   NIM          : ").strip() or 'Tidak dicantumkan'
        thn_masuk = input("   Tahun Masuk  : ").strip() or 'Tidak dicantumkan'
        tgl_lulus = input("   Tanggal Lulus: ").strip() or 'Tidak dicantumkan'
        fakultas  = input("   Fakultas     : ").strip() or 'Tidak dicantumkan'
        prodi     = input("   Program Studi: ").strip() or 'Tidak dicantumkan'

        print(f"\n🔎 Mencari: {first_name} {last_name} | {key_mgr.status()}")

        ok, items = panggil_apify(key_mgr, first_name, last_name)

        if ok is None:
            print("Program dihentikan.")
            break

        if ok and items:
            disimpan = proses_hasil(items, nama_input, nim_asli, thn_masuk,
                                    tgl_lulus, fakultas, prodi, file_output,
                                    filter_umm=filter_umm)
            if disimpan:
                counter += 1
                label = "Alumni UMM" if filter_umm else "Profil"
                print(f"   => ✅ DATA DISIMPAN: {label} ditemukan. (Total: {counter})")
            else:
                label = "bukan Alumni UMM" if filter_umm else "tidak ada profil cocok"
                print(f"   => ❌ DIABAIKAN: {label}.")
        else:
            print("   => ❌ DIABAIKAN: Tidak ditemukan profil di LinkedIn.")

    if counter > 0:
        print(f"\n🎉 SELESAI! {counter} data tersimpan di: {file_output}")
    else:
        print("\nℹ️  Tidak ada data yang disimpan.")
