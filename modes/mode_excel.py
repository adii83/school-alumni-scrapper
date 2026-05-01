import pandas as pd
from config           import FILE_INPUT
from core.checkpoint  import simpan_checkpoint, muat_checkpoint, hapus_checkpoint
from core.apify_service import panggil_apify, proses_hasil
from core.api_manager import ApiKeyManager
from utils.name_utils import pisahkan_nama


def mode_excel(key_mgr: ApiKeyManager) -> None:
    """Scraping massal dari Data Alumni.xlsx dengan dukungan resume/checkpoint."""

    checkpoint       = muat_checkpoint()
    resume_mode      = False
    last_excel_index = -1

    if checkpoint:
        print(f"\n📌 CHECKPOINT DITEMUKAN!")
        print(f"   Batch  : Baris {checkpoint['mulai_baris']} s/d {checkpoint['baris_akhir']}")
        print(f"   Terakhir diproses : indeks #{checkpoint['last_excel_index'] + 1}")
        print(f"   Output : {checkpoint['file_output']}")
        if input("   Lanjutkan dari checkpoint? (y/n): ").strip().lower() == 'y':
            resume_mode      = True
            mulai_baris      = checkpoint['mulai_baris']
            baris_akhir      = checkpoint['baris_akhir']
            jumlah_proses    = baris_akhir - mulai_baris + 1
            file_output      = checkpoint['file_output']
            last_excel_index = checkpoint['last_excel_index']
            saved_key_idx    = checkpoint.get('current_key_index', 0)
            if saved_key_idx < len(key_mgr.keys):
                key_mgr.current_index = saved_key_idx

    print("\nMembaca file Excel...")
    try:
        df = pd.read_excel(FILE_INPUT)
    except FileNotFoundError:
        print(f"Error: File '{FILE_INPUT}' tidak ditemukan.")
        return
    except Exception as e:
        print(f"Error saat membaca Excel: {e}")
        return

    total_data = len(df)
    print(f"Total data di Excel: {total_data} baris.")

    if not resume_mode:
        try:
            mulai_baris   = int(input(f"👉 Mulai dari baris ke berapa? (1 - {total_data}): "))
            jumlah_proses = int(input("👉 Berapa banyak data yang ingin diproses?: "))
        except ValueError:
            print("Harap masukkan angka yang valid!")
            return
        baris_akhir = mulai_baris + jumlah_proses - 1
        file_output = f'data_{mulai_baris}_{baris_akhir}.csv'

    index_awal = mulai_baris - 1
    df_subset  = df.iloc[index_awal: index_awal + jumlah_proses]

    print(f"\nMemproses {len(df_subset)} data (Baris {mulai_baris} s/d {baris_akhir})...")
    if resume_mode:
        print(f"▶️  Melanjutkan dari setelah indeks #{last_excel_index + 1}...")
    print()

    for step, (index, row) in enumerate(df_subset.iterrows(), start=1):
        if resume_mode and index <= last_excel_index:
            continue

        nama_asli = row.get('Nama Lulusan', '')
        nim_asli  = row.get('NIM',           'Tidak dicantumkan')
        thn_masuk = row.get('Tahun Masuk',   'Tidak dicantumkan')
        tgl_lulus = row.get('Tanggal Lulus', 'Tidak dicantumkan')
        fakultas  = row.get('Fakultas',      'Tidak dicantumkan')
        prodi     = row.get('Program Studi', 'Tidak dicantumkan')

        first_name, last_name = pisahkan_nama(nama_asli)

        print("\n" + "-" * 55)
        print(f"🔄 PROGRESS : {step}/{len(df_subset)} | {key_mgr.status()}")
        print(f"📍 EXCEL    : Baris ke-{index + 1}")

        if not first_name and not last_name:
            print("⚠️  INFO     : Baris kosong, diabaikan.")
            simpan_checkpoint({
                'mulai_baris': mulai_baris, 'baris_akhir': baris_akhir,
                'file_output': file_output, 'last_excel_index': index,
                'current_key_index': key_mgr.current_index,
            })
            continue

        print(f"👤 MENCARI  : {first_name} | {last_name}")

        cp = {
            'mulai_baris': mulai_baris, 'baris_akhir': baris_akhir,
            'file_output': file_output, 'last_excel_index': index - 1,
            'current_key_index': key_mgr.current_index,
        }

        ok, items = panggil_apify(key_mgr, first_name, last_name, checkpoint_data=cp)

        if ok is None:
            print("Program dihentikan. Checkpoint tersimpan, bisa dilanjutkan nanti.")
            return

        if ok and items:
            disimpan = proses_hasil(items, nama_asli, nim_asli, thn_masuk,
                                    tgl_lulus, fakultas, prodi, file_output,
                                    filter_umm=True)
            print(f"   => {'✅ DATA DISIMPAN: Alumni UMM terdeteksi.' if disimpan else '❌ DIABAIKAN: Bukan Alumni UMM.'}")
        else:
            print("   => ❌ DIABAIKAN: Tidak ditemukan profil.")

        simpan_checkpoint({
            'mulai_baris': mulai_baris, 'baris_akhir': baris_akhir,
            'file_output': file_output, 'last_excel_index': index,
            'current_key_index': key_mgr.current_index,
        })

    print(f"\n🎉 SELESAI! Hasil tersimpan di: {file_output}")
    hapus_checkpoint()
    print("🗑️  Checkpoint dihapus (batch selesai sempurna).")
