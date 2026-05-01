import os
import pandas as pd
from utils.classifier import klasifikasi_status

_DEFAULT = 'Tidak dicantumkan'
_PRIVATE = 'Tidak publik'


def ekstrak_item(item: dict, nama_asli, nim_asli, thn_masuk,
                 tgl_lulus, fakultas, prodi) -> dict:
    """Ekstrak satu item hasil Apify menjadi dict baris CSV."""

    headline = str(item.get('headline') or _DEFAULT).strip()
    url      = item.get('url') or item.get('linkedinUrl') or _DEFAULT

    email_list = item.get('emails', [])
    email = item.get('email') or (
        email_list[0].get('email', _PRIVATE)
        if isinstance(email_list, list) and len(email_list) > 0
        else _PRIVATE
    )

    raw_lokasi = item.get('location')
    lokasi = (
        raw_lokasi.get('linkedinText', _DEFAULT)
        if isinstance(raw_lokasi, dict)
        else (str(raw_lokasi) if raw_lokasi else _DEFAULT)
    )

    tempat_p  = posisi_p  = sosmed_p  = _DEFAULT
    tempat_t  = posisi_t  = sosmed_t  = _DEFAULT
    status_p  = "Tidak Ada Pekerjaan Aktif"
    status_t  = "Belum Pernah Bekerja"

    pengalaman = item.get('experience') or item.get('currentPosition')
    if pengalaman and isinstance(pengalaman, list) and len(pengalaman) > 0:

        p1   = pengalaman[0]
        cn1  = str(p1.get('companyName')       or _DEFAULT).strip()
        occ1 = str(p1.get('position')          or _DEFAULT).strip()
        sm1  = str(p1.get('companyLinkedinUrl') or _DEFAULT)

        end1   = p1.get('endDate')
        resign = end1 and 'year' in end1 and end1['year'] < 2026
        if resign:
            cn1 = f"{cn1} (Resign {end1['year']})"

        if resign:
            tempat_t, posisi_t = cn1, occ1
            status_t  = klasifikasi_status(headline, cn1, occ1)
            sosmed_t  = sm1
        else:
            tempat_p, posisi_p = cn1, occ1
            status_p  = klasifikasi_status(headline, cn1, occ1)
            sosmed_p  = sm1

            if len(pengalaman) > 1:
                p2   = pengalaman[1]
                cn2  = str(p2.get('companyName')       or _DEFAULT).strip()
                occ2 = str(p2.get('position')          or _DEFAULT).strip()
                sm2  = str(p2.get('companyLinkedinUrl') or _DEFAULT)
                end2 = p2.get('endDate')
                if end2 and 'year' in end2:
                    cn2 = f"{cn2} (Resign {end2['year']})"
                tempat_t, posisi_t = cn2, occ2
                status_t  = klasifikasi_status("", cn2, occ2)
                sosmed_t  = sm2

    return {
        'Nama Lulusan':               nama_asli,
        'NIM':                        nim_asli,
        'Tahun Masuk':                thn_masuk,
        'Tanggal Lulus':              tgl_lulus,
        'Fakultas':                   fakultas,
        'Program Studi':              prodi,
        'Linkedin':                   url,
        'Email':                      email,
        'Alamat Bekerja':             lokasi,
        'Tempat Bekerja (Present)':   tempat_p,
        'Posisi Jabatan (Present)':   posisi_p,
        'Status Pekerjaan (Present)': status_p,
        'Sosmed Kantor (Present)':    sosmed_p,
        'Tempat Bekerja (Terakhir)':  tempat_t,
        'Posisi Jabatan (Terakhir)':  posisi_t,
        'Status Pekerjaan (Terakhir)':status_t,
        'Sosmed Kantor (Terakhir)':   sosmed_t,
        'Instagram':                  _PRIVATE,
        'TikTok':                     _PRIVATE,
        'Facebook':                   _PRIVATE,
        'Nomor HP':                   _PRIVATE,
    }


def simpan_ke_csv(file_output: str, baris: dict) -> None:
    """Tambahkan satu baris ke file CSV (buat jika belum ada)."""
    df = pd.DataFrame([baris])
    if not os.path.isfile(file_output):
        df.to_csv(file_output, index=False, mode='w', encoding='utf-8')
    else:
        df.to_csv(file_output, index=False, mode='a', header=False, encoding='utf-8')
