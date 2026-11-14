# -*- coding: utf-8 -*-
"""Validasi bekas bakar NISAR terhadap titik panas NASA FIRMS.

Peta penurunan HV menunjukkan "tajuk hilang" — belum tentu terbakar. Panen,
penebangan, dan genangan juga menekan hamburan silang. FIRMS (VIIRS/MODIS)
memberi bukti independen: di mana api benar-benar terdeteksi.

Kunci diambil dari variabel lingkungan FIRMS_MAP_KEY (jangan ditaruh di berkas
yang dipantau editor):

    PowerShell : $env:FIRMS_MAP_KEY = "..."
    bash       : export FIRMS_MAP_KEY=...

Ambil kunci gratis di https://firms.modaps.eosdis.nasa.gov/api/map_key
"""
from __future__ import annotations

import io
import os
import sys
import time
import datetime as dt

import numpy as np
import pandas as pd
import requests

# kotak bingkai NISAR 155A/002 (dari k155_pra.npz)
BBOX = (107.30, -0.58, 110.31, 2.38)          # barat, selatan, timur, utara
AWAL, AKHIR = dt.date(2026, 6, 24), dt.date(2026, 9, 16)
# SP (standard processing) tertinggal ~3 bulan; untuk kejadian baru hanya NRT
# yang tersedia. Dicoba berurutan, yang pertama mengembalikan data dipakai.
SUMBER = ["VIIRS_SNPP_SP", "VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"]
KELUAR = "nisar/kalbar/firms.csv"


def kunci() -> str:
    k = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not k:
        sys.exit("FIRMS_MAP_KEY belum dipasang. Lihat docstring berkas ini.")
    return k


def ambil(k: str) -> pd.DataFrame:
    """FIRMS membatasi 1-5 hari per permintaan. Untuk tiap potongan, sumber
    dicoba berurutan sampai ada yang mengembalikan baris."""
    bbox = ",".join(str(v) for v in BBOX)
    potong, t = [], AWAL
    while t <= AKHIR:
        n = min(5, (AKHIR - t).days + 1)
        dapat = None
        for src in SUMBER:
            url = ("https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
                   f"{k}/{src}/{bbox}/{n}/{t.isoformat()}")
            try:
                r = requests.get(url, timeout=120)
            except Exception as e:
                print(f"  {t} {src:<17} galat jaringan {type(e).__name__}")
                continue
            teks = r.text.lstrip()
            if r.status_code != 200 or teks.lower().startswith(("invalid", "error")):
                print(f"  {t} {src:<17} HTTP {r.status_code} {teks[:60]}")
                continue
            d = pd.read_csv(io.StringIO(r.text))
            if len(d):
                d["sumber"] = src
                dapat = d
                print(f"  {t} .. +{n}h  {src:<17} {len(d):>6} titik")
                break
            print(f"  {t} {src:<17} kosong")
            time.sleep(0.5)
        if dapat is None:
            print(f"  {t} .. +{n}h  TIDAK ADA sumber yang memberi data")
        else:
            potong.append(dapat)
        t += dt.timedelta(days=n)
        time.sleep(1.0)
    if not potong:
        sys.exit("Tidak ada data terambil dari sumber mana pun.")
    return pd.concat(potong, ignore_index=True)


def main() -> None:
    if os.path.exists(KELUAR) and os.environ.get("FIRMS_PAKAI_CACHE","1")=="1":
        hs = pd.read_csv(KELUAR)
        print(f"memakai berkas yang ada: {KELUAR} ({len(hs):,} titik)")
    else:
        hs = ambil(kunci())
        os.makedirs(os.path.dirname(KELUAR), exist_ok=True)
        hs.to_csv(KELUAR, index=False)
        print(f"\n{len(hs):,} titik panas -> {KELUAR}")

    print("\nkolom:", list(hs.columns))
    if "confidence" in hs:
        print("kepercayaan:", hs["confidence"].value_counts().to_dict())

    # --- tumpangkan ke peta penurunan HV -----------------------------------
    from pyproj import Transformer
    a = np.load("nisar/kalbar/k155_pra.npz")
    b = np.load("nisar/kalbar/k155_pasca.npz")
    hv0, hv1, x, y = a["hv"], b["hv"], a["x"], a["y"]
    sah = np.isfinite(hv0) & np.isfinite(hv1) & (hv0 > 0) & (hv1 > 0)
    dB = np.where(sah, 10 * np.log10(np.where(sah, hv1, 1) / np.where(sah, hv0, 1)), np.nan)

    tf = Transformer.from_crs("EPSG:4326", f"EPSG:{int(a['epsg'])}", always_xy=True)
    hx, hy = tf.transform(hs["longitude"].values, hs["latitude"].values)
    # PENTING: y pada produk NISAR MENURUN (utara -> selatan). searchsorted
    # mengandaikan menaik, jadi tanpa pembalikan seluruh indeks meleset dan
    # setiap titik panas mendarat di piksel NaN.
    ix = np.searchsorted(x, hx).clip(0, len(x) - 1)
    iy = (np.searchsorted(-y, -hy) if y[0] > y[-1]
          else np.searchsorted(y, hy)).clip(0, len(y) - 1)
    di = dB[iy, ix]
    ada = np.isfinite(di)
    print(f"\ntitik panas di dalam bingkai & piksel sah: {ada.sum():,} dari {len(hs):,}")

    print("\nSEBARAN dB DI LOKASI TITIK PANAS vs SELURUH BINGKAI:")
    print(f"{'persentil':<12}{'di titik panas':>16}{'seluruh bingkai':>18}")
    for q in (5, 25, 50, 75, 95):
        print(f"  p{q:<10}{np.nanpercentile(di[ada], q):>15.2f}"
              f"{np.nanpercentile(dB, q):>18.2f}")

    for t in (-2, -3, -4):
        pa = float(np.mean(di[ada] < t))
        pb = float(np.nanmean(dB < t))
        print(f"\n  bagian < {t} dB  di titik panas {pa:6.1%} | seluruh bingkai {pb:6.1%}"
              f"  -> pengayaan {pa/max(pb,1e-9):5.1f}x")


if __name__ == "__main__":
    main()
