# -*- coding: utf-8 -*-
"""Titik karhutla untuk peta: lokasi yang DIKONFIRMASI DUA SUMBER.

Pusat bingkai radar (cari_koordinat.py) jatuh di LAUT lepas Singkawang:
bingkai persegi panjang itu sebagian menutupi laut. Untuk penanda peta yang
dipakai adalah titik panas FIRMS yang JUGA menunjukkan penurunan hamburan
balik HV >= 3 dB (ambang yang sama dengan firms_validasi.py) -- api menurut
satelit optik/termal DAN bekas bakar menurut radar.

Dari titik-titik itu dipilih SEL 0,1 derajat (~11 km) yang paling padat, lalu
diambil median koordinatnya. Median, bukan rata-rata: kelompok api yang
terpencar membuat rata-rata bisa jatuh di antara dua kelompok, termasuk di
tempat yang tidak terbakar.
"""
import numpy as np
import pandas as pd
from pyproj import Transformer

a = np.load("kalbar/k155_pra.npz")
b = np.load("kalbar/k155_pasca.npz")
hv0, hv1, x, y = a["hv"], b["hv"], a["x"], a["y"]
sah = np.isfinite(hv0) & np.isfinite(hv1) & (hv0 > 0) & (hv1 > 0)
dB = np.where(sah, 10 * np.log10(np.where(sah, hv1, 1) / np.where(sah, hv0, 1)), np.nan)

f = pd.read_csv("kalbar/firms.csv")
ke_peta = Transformer.from_crs(4326, int(a["epsg"]), always_xy=True)
fx, fy = ke_peta.transform(f["longitude"].values, f["latitude"].values)

# Pengindeksan SAMA PERSIS dengan firms_validasi.py, supaya angkanya sebanding.
# y MENURUN (jebakan NISAR no. 4), jadi dibalik tandanya untuk searchsorted.
ix = np.searchsorted(x, fx).clip(0, len(x) - 1)
iy = (np.searchsorted(-y, -fy) if y[0] > y[-1] else np.searchsorted(y, fy)).clip(0, len(y) - 1)
nilai = dB[iy, ix]
ada = np.isfinite(nilai)
print(f"piksel radar sah di lokasi titik panas: {int(ada.sum()):,} dari {len(f):,}")
print(f"bagian < -3 dB di antara yang sah: {np.mean(nilai[ada] < -3):.1%} "
      f"(catatan memori: 4,4%)")

kena = f[ada & (nilai < -3)].copy()
print(f"titik panas yang JUGA turun > 3 dB di radar: {len(kena):,}")

# Kepadatan per TITIK (jumlah tetangga dalam radius ~11 km), bukan per sel
# grid. Sel 0,1 derajat memotong kelompok: tiga sel bertetangga di lintang
# 0,45-0,55 berisi 27 titik bersama, tapi masing-masing kalah dari satu sel
# berisi 12. Kepadatan per titik tidak punya garis potong.
R = 0.1                                                     # derajat, ~11 km
la, lo = kena["latitude"].values, kena["longitude"].values
jarak = np.hypot(la[:, None] - la[None, :], lo[:, None] - lo[None, :])
tetangga = (jarak < R).sum(1)
pusat = int(np.argmax(tetangga))
kelompok = jarak[pusat] < R
print()
print(f"kelompok terpadat: {int(kelompok.sum())} titik terkonfirmasi dalam {R} derajat")
print(f"-> PAKAI: lat {np.median(la[kelompok]):.3f}, lon {np.median(lo[kelompok]):.3f}")
