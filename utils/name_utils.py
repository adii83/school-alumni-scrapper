import pandas as pd


def pisahkan_nama(nama_lengkap) -> tuple[str, str]:
    """
    Pisahkan nama lengkap menjadi (first_name, last_name).
    Nama dengan 3+ kata: 2 kata pertama → first, sisanya → last.
    """
    if pd.isna(nama_lengkap) or str(nama_lengkap).strip() == "" or str(nama_lengkap).lower() == "nan":
        return "", ""

    kata = str(nama_lengkap).strip().split()
    if len(kata) == 0:   return "", ""
    elif len(kata) == 1: return kata[0], ""
    elif len(kata) == 2: return kata[0], kata[1]
    else:
        return " ".join(kata[:2]), " ".join(kata[2:])
