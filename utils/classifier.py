_KEYWORDS = {
    "Mahasiswa / Magang":    ['intern', 'magang', 'asisten', 'student', 'mahasiswa'],
    "BUMN / BUMD":           ['bumn', 'telkom', 'pertamina', 'pln', 'pt kai', 'pelindo',
                              'angkasa pura', 'mandiri', 'bri', 'bni', 'btn', 'pegadaian'],
    "PNS / Pemerintahan":    ['kementerian', 'dinas', 'pemerintah', 'pemkot', 'pemkab',
                              'pemprov', 'badan pusat', 'asn', 'cpns', 'puskesmas', 'rsud',
                              'kpu', 'bawaslu', 'polri', 'tni', 'kejaksaan'],
    "Pendidikan / Akademisi":['guru', 'dosen', 'teacher', 'lecturer', 'sekolah',
                              'universitas', 'institute', 'politeknik', 'yayasan pendidikan'],
    "Wirausaha / Freelance": ['owner', 'founder', 'co-founder', 'ceo', 'wirausaha',
                              'entrepreneur', 'self-employed', 'freelance', 'pekerja lepas',
                              'business owner', 'self employed'],
}


def klasifikasi_status(headline: str, company: str, occupation: str) -> str:
    """Klasifikasikan pekerjaan alumni ke dalam satu dari 6 kategori."""
    teks = f"{headline} {company} {occupation}".lower()
    for kategori, keywords in _KEYWORDS.items():
        if any(k in teks for k in keywords):
            return kategori
    if company == 'Tidak dicantumkan' and occupation == 'Tidak dicantumkan':
        return "Tidak Ada Data Pekerjaan"
    return "Swasta"
