import time
from core.api_manager import ApiKeyManager
from utils.data_extractor import ekstrak_item, simpan_ke_csv
from config import APIFY_ACTOR, TARGET_UNI, MAX_RETRIES, MAX_RESULTS


def panggil_apify(
    key_mgr: ApiKeyManager,
    first_name: str,
    last_name: str,
    checkpoint_data: dict | None = None
) -> tuple[bool | None, list | None]:
    """
    Panggil Apify actor dengan retry & auto-rotate key.

    Return:
        (True,  items) — berhasil
        (False, None)  — gagal setelah semua retry
        (None,  None)  — user memilih keluar
    """
    run_input = {
        "firstName":          first_name,
        "lastName":           last_name,
        "profileScraperMode": "Full + email search",
        "strictSearch":       False,
        "maxPages":           1,
    }

    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            client = key_mgr.get_client()
            run    = client.actor(APIFY_ACTOR).call(run_input=run_input)
            items  = client.dataset(run["defaultDatasetId"]).list_items().items
            return True, items

        except Exception as e:
            err      = str(e).lower()
            is_quota = any(k in err for k in
                           ['credit', 'limit', '402', 'payment', 'quota', 'insufficient'])

            if is_quota:
                print(f"\n🛑 SALDO KEY #{key_mgr.current_index + 1} HABIS!")
                if key_mgr.rotate():
                    continue

                print("🛑 SEMUA API KEY HABIS! Silakan tambah key baru di GUI.")
                return None, None

            attempt += 1
            if attempt < MAX_RETRIES:
                print(f"   ⏳ Retry {attempt}/{MAX_RETRIES - 1}... ({str(e)[:60]})")
                time.sleep(3)

    return False, None


def proses_hasil(
    dataset_items: list,
    nama_asli, nim_asli, thn_masuk, tgl_lulus,
    fakultas, prodi,
    file_output: str,
    filter_umm: bool = True
) -> bool:
    """
    Filter hasil Apify, ekstrak data, dan simpan ke CSV.
    Return True jika minimal satu item berhasil disimpan.
    """
    for item in dataset_items[:MAX_RESULTS]:
        school_info = str(item.get('school',      '')).lower()
        edu_info    = str(item.get('education',   '')).lower()
        desc_info   = str(item.get('description', '')).lower()

        lolos = (
            TARGET_UNI in school_info or
            TARGET_UNI in edu_info   or
            TARGET_UNI in desc_info
        ) if filter_umm else True

        if lolos:
            baris = ekstrak_item(item, nama_asli, nim_asli, thn_masuk,
                                 tgl_lulus, fakultas, prodi)
            simpan_ke_csv(file_output, baris)
            return True

    return False
