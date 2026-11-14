# -*- coding: utf-8 -*-
"""Cari koordinat pusat (lintang, bujur) setiap data NISAR yang sudah dipotong.

Berkas .npz menyimpan sumbu x/y dalam satuan PROYEKSI (meter UTM untuk GCOV/
GUNW, meter EASE-Grid 2.0 untuk SME2), bukan derajat -- jebakan NISAR nomor 2
dan 7. Jadi pusatnya diubah ke lintang/bujur memakai EPSG yang tersimpan di
berkas itu sendiri.
"""
import glob
import numpy as np

BERKAS = {
    "Karhutla Kalimantan Barat": "kalbar/k155_pra.npz",
    "El Nino (SME2)": "sme2/sm_2026-06-25.npz",
    "Gempa Flores": "flores/koseismik_093.npz",
}

for nama, p in BERKAS.items():
    d = np.load(p, allow_pickle=True)
    print(f"--- {nama}: {p}")
    for k in d.files:
        v = d[k]
        info = f"shape {v.shape}" if v.ndim else f"= {v.item()!r}"
        print(f"    {k:<20} {v.dtype}  {info}")

# --- ubah pusat + sudut ke lintang/bujur ------------------------------------
from pyproj import Transformer

print("\n" + "=" * 70)
print("Koordinat untuk TEMUAN di index.html  (Leaflet: [lintang, bujur])")
print("=" * 70)
for nama, p in BERKAS.items():
    d = np.load(p, allow_pickle=True)
    ke_derajat = Transformer.from_crs(int(d["epsg"]), 4326, always_xy=True)
    x, y = d["x"], d["y"]
    lon, lat = ke_derajat.transform(x.mean(), y.mean())
    # sudut bingkai, untuk memeriksa bahwa pusatnya masuk akal
    bujur, lintang = ke_derajat.transform([x.min(), x.max()], [y.min(), y.max()])
    print(f"{nama:<28} lat {lat:8.3f}  lon {lon:8.3f}   "
          f"(bingkai lat {min(lintang):.2f}..{max(lintang):.2f}, "
          f"lon {min(bujur):.2f}..{max(bujur):.2f})")
