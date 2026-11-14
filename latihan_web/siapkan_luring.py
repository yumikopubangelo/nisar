# -*- coding: utf-8 -*-
"""Siapkan semua berkas supaya lengkap.html jalan TANPA internet (untuk expo).

Jalankan dari folder nisar/:   python latihan_web/siapkan_luring.py [--hitung]

Yang diunduh ke latihan_web/lib/:
  leaflet/      leaflet.js, leaflet.css, images/ (ikon tombol lapisan)
  chart.umd.min.js
  ubin/{z}/{y}/{x}.jpg   citra Sentinel-2 cloudless 2024 (EOX), hanya
                         wilayah x zoom yang dipakai keempat cerita

KENAPA EOX, BUKAN ESRI. Ketentuan layanan Esri tidak mengizinkan ubin peta
dasarnya disimpan untuk dipakai luring. Sentinel-2 cloudless dari EOX
berlisensi CC BY-NC-SA 4.0 (versi 2018 ke atas -- perlu dicek ulang di
s2maps.eu): boleh disimpan dan ditampilkan untuk keperluan NON-komersial
seperti expo kampus, dengan atribusi. Atribusinya ada di lengkap.html.

Sopan pada server: permintaan berurutan dengan jeda, dan ubin yang sudah ada
tidak diunduh ulang (skrip ini aman dijalankan berkali-kali).
"""
import math
import sys
import time
import urllib.request
from pathlib import Path

LIB = Path("latihan_web/lib")
UBIN = LIB / "ubin"
URL_UBIN = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg"
KEPALA = {"User-Agent": "Mozilla/5.0 (latihan expo NISAR, Universitas Siliwangi)"}

PUSTAKA = {
    "leaflet/leaflet.js": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js",
    "leaflet/leaflet.css": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css",
    "leaflet/images/layers.png": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/layers.png",
    "leaflet/images/layers-2x.png": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/layers-2x.png",
    "chart.umd.min.js": "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js",
}

# (nama, lat_min, lon_min, lat_max, lon_max, zoom_min, zoom_maks)
# Diturunkan dari CERITA di lengkap.html: pusat + zoom tiap cerita, diberi
# kelonggaran 1-2 tingkat zoom ke atas dan ke bawah untuk pemakai yang
# memperbesar/memperkecil.
#
# Dilebarkan 3 Okt 2026: wilayah pertama terlalu sempit untuk layar lebar,
# tepi peta tampil abu-abu (uji di 1400 px). Ukurannya kini diturunkan dari
# layar 1920 px di zoom awal tiap cerita: lebar terlihat (derajat) =
# lebar_px / 256 * 360 / 2^zoom. Di zoom 12 itu 0,66 derajat, di zoom 7 21.
WILAYAH = [
    ("Indonesia",  -12.0,  92.0,   8.0, 144.0,  4,  6),
    ("Kalimantan",  -6.0, 100.0,   6.0, 121.0,  7,  7),
    ("Kalimantan", -4.0, 103.5,   4.0, 117.0,  8,  8),
    ("Kalbar",      -1.0, 106.8,   2.6, 111.0,  9, 10),
    ("Krakatau",    -6.45, 104.95, -5.75, 105.90, 10, 13),
    ("Krakatau",    -6.20, 105.30, -6.00, 105.55, 14, 14),
]


def ke_ubin(lat, lon, z):
    """Rumus Web Mercator (EPSG:3857) -> nomor ubin. Sama dengan yang dipakai Leaflet."""
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


def daftar_ubin():
    semua = set()
    for _, s, w, n, e, z0, z1 in WILAYAH:
        for z in range(z0, z1 + 1):
            x0, y0 = ke_ubin(n, w, z)          # sudut barat laut -> y terkecil
            x1, y1 = ke_ubin(s, e, z)          # sudut tenggara  -> y terbesar
            for x in range(x0, x1 + 1):
                for y in range(y0, y1 + 1):
                    semua.add((z, y, x))
    return sorted(semua)


def unduh(url, tujuan):
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    data = urllib.request.urlopen(urllib.request.Request(url, headers=KEPALA), timeout=60).read()
    tujuan.write_bytes(data)
    return len(data)


if __name__ == "__main__":
    ubin = daftar_ubin()
    print(f"ubin yang dibutuhkan: {len(ubin)}")
    for z in sorted({u[0] for u in ubin}):
        print(f"  zoom {z:>2}: {sum(1 for u in ubin if u[0] == z)}")
    if "--hitung" in sys.argv:
        sys.exit(0)

    for rel, url in PUSTAKA.items():
        p = LIB / rel
        if not p.exists():
            print(f"pustaka {rel}: {unduh(url, p) // 1024} KB")

    baru = total = 0
    for i, (z, y, x) in enumerate(ubin, 1):
        p = UBIN / str(z) / str(y) / f"{x}.jpg"
        if p.exists():
            continue
        total += unduh(URL_UBIN.format(z=z, y=y, x=x), p)
        baru += 1
        time.sleep(0.05)
        if i % 100 == 0:
            print(f"  {i}/{len(ubin)}")
    print(f"selesai: {baru} ubin baru, {total / 1048576:.1f} MB")
