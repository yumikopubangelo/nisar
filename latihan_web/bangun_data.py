# -*- coding: utf-8 -*-
"""Panggang data NISAR menjadi lapisan peta + grid kecil untuk website.

Jalankan dari folder nisar/:   python latihan_web/bangun_data.py

Keluaran (semua di latihan_web/data/):
  *.png    gambar transparan per tanggal, SUDAH dalam grid lintang/bujur biasa,
           sehingga Leaflet cukup menempelkannya di antara dua sudut.
  data.js  `window.NISAR = {...}`: batas, tanggal, nama gambar, dan grid kasar
           per tanggal untuk grafik deret waktu saat piksel diklik.

Kenapa .js dan bukan .json: halaman yang dibuka lewat file:// (klik dua kali)
DILARANG browser memakai fetch() ke berkas lokal. <script src="data.js">
boleh. Jadi data dimuat sebagai skrip.

KENAPA PERLU DIPROYEKSIKAN ULANG. Data NISAR ada dalam meter UTM (GUNW/GCOV)
atau meter EASE-Grid 2.0 (SME2), bukan derajat (jebakan NISAR no. 2 dan 7).
Bingkainya juga MIRING terhadap utara. Leaflet hanya bisa menempelkan gambar
persegi sejajar lintang/bujur. Maka setiap piksel grid lintang/bujur tujuan
dicari asal-usulnya di grid sumber (tetangga terdekat):

    (lat, lon) tujuan --pyproj--> (x, y) sumber --searchsorted--> indeks --> nilai

Arah ini (tujuan -> sumber) sengaja dipakai, bukan sumber -> tujuan: setiap
piksel tujuan dijamin terisi tepat sekali, tanpa lubang.
"""
import glob
import json
from pathlib import Path

import numpy as np
from matplotlib import colormaps
from PIL import Image
from pyproj import Transformer

KELUAR = Path("latihan_web/data")
KELUAR.mkdir(parents=True, exist_ok=True)


def batas_latlon(x, y, epsg):
    """Kotak lintang/bujur yang memuat seluruh bingkai (dari keliling bingkai)."""
    t = Transformer.from_crs(epsg, 4326, always_xy=True)
    keliling_x = np.concatenate([x, x, np.full(len(y), x[0]), np.full(len(y), x[-1])])
    keliling_y = np.concatenate([np.full(len(x), y[0]), np.full(len(x), y[-1]), y, y])
    lon, lat = t.transform(keliling_x, keliling_y)
    return float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())


def proyeksikan(nilai, x, y, epsg, batas, n_lebar):
    """Grid sumber (x naik, y turun) -> grid lintang/bujur biasa, tetangga terdekat."""
    s, w, n, e = batas
    n_tinggi = max(1, round(n_lebar * (n - s) / (e - w)))
    lon = np.linspace(w, e, n_lebar)
    lat = np.linspace(n, s, n_tinggi)                    # baris 0 = utara (seperti gambar)
    LON, LAT = np.meshgrid(lon, lat)
    t = Transformer.from_crs(4326, epsg, always_xy=True)
    X, Y = t.transform(LON, LAT)
    dx, dy = x[1] - x[0], y[1] - y[0]                    # dy NEGATIF (y turun)
    ix = np.rint((X - x[0]) / dx).astype(int)
    iy = np.rint((Y - y[0]) / dy).astype(int)
    di = (ix >= 0) & (ix < len(x)) & (iy >= 0) & (iy < len(y))
    keluar = np.full(LON.shape, np.nan, np.float32)
    keluar[di] = nilai[iy[di], ix[di]]
    return keluar


def ke_png(grid, nama, cmap, vmin, vmax, alpha=0.85):
    """NaN -> transparan. Nilai dinormalkan ke [0,1] lalu diwarnai."""
    norm = np.clip((grid - vmin) / (vmax - vmin), 0, 1)
    rgba = (colormaps[cmap](np.nan_to_num(norm)) * 255).astype(np.uint8)
    rgba[..., 3] = np.where(np.isfinite(grid), int(alpha * 255), 0)
    Image.fromarray(rgba, "RGBA").save(KELUAR / nama, optimize=True)
    return nama


def kasar(grid, n_lebar):
    """Grid kecil untuk grafik klik: rata-rata blok, NaN diabaikan, 3 desimal."""
    f = max(1, grid.shape[1] // n_lebar)
    h, w = (grid.shape[0] // f) * f, (grid.shape[1] // f) * f
    b = grid[:h, :w].reshape(h // f, f, w // f, f)
    with np.errstate(invalid="ignore"):
        m = np.nanmean(b, axis=(1, 3))
    return [[None if not np.isfinite(v) else round(float(v), 3) for v in baris] for baris in m]


DATA = {}

# ------------------------------------------------------------- 1. Krakatau
PERIODE = ["pra1", "pra2", "pra3", "pra4", "LETUSAN", "pasca"]
d0 = np.load("krakatau/pra1.npz")
x, y, epsg = d0["x"], d0["y"], int(d0["epsg"])
batas = batas_latlon(x, y, epsg)
# Topeng darat SAMA PERSIS dengan krakatau_koherensi.topeng_darat(): rata-rata
# koherensi pra1..pra3 > 0,35. Air laut TIDAK bernilai 0 -- koherensinya derau
# sekitar 0,2 -- jadi menyaring `koh <= 0` membiarkan seluruh laut terwarnai.
# Topeng hanya dari periode PRA: kalau periode letusan ikut, pulau yang
# koherensinya runtuh justru terbuang dari topengnya sendiri.
darat = np.mean([np.load(f"krakatau/{p}.npz")["koh"] for p in ("pra1", "pra2", "pra3")], axis=0) > 0.35
lapisan, grid, tanggal = [], [], []
for p in PERIODE:
    d = np.load(f"krakatau/{p}.npz")
    koh = d["koh"].astype(np.float32)
    koh[~darat] = np.nan
    g = proyeksikan(koh, x, y, epsg, batas, 600)
    lapisan.append(ke_png(g, f"krakatau_{p}.png", "viridis", 0, 1))
    grid.append(kasar(g, 75))
    a, b = str(d["pas"]).split("->")
    tanggal.append(f"{a[6:8]}/{a[4:6]} → {b[6:8]}/{b[4:6]}" + (" (LETUSAN)" if p == "LETUSAN" else ""))
DATA["krakatau"] = dict(judul="Koherensi radar, Anak Krakatau", satuan="koherensi",
                        batas=batas, tanggal=tanggal, lapisan=lapisan, grid=grid,
                        skala=dict(cmap="viridis", min=0, max=1))
print("krakatau:", len(PERIODE), "periode, batas", [round(v, 3) for v in batas])

# ------------------------------------------------------------- 2. El Nino (SME2)
for kunci, folder, label in (("sme2_kalteng", "sme2", "Kalimantan Tengah"),
                             ("sme2_kalbar", "sme2_155", "Kalimantan Barat")):
    berkas = sorted(glob.glob(f"{folder}/sm_*.npz"))
    d0 = np.load(berkas[0])
    x, y, epsg = d0["x"], d0["y"], int(d0["epsg"])
    batas = batas_latlon(x, y, epsg)
    lapisan, grid, tanggal = [], [], []
    for f in berkas:
        d = np.load(f)
        sm = d["sm"].astype(np.float32)
        sm[(sm < 0) | (d["wf"] > 0.5)] = np.nan          # -9999 = isian; buang badan air
        g = proyeksikan(sm, x, y, epsg, batas, 500)
        t = str(d["tanggal"])
        lapisan.append(ke_png(g, f"{kunci}_{t}.png", "BrBG", 0.05, 0.5))
        grid.append(kasar(g, 60))
        tanggal.append(t)
    DATA[kunci] = dict(judul=f"Kelembapan tanah SME2, {label}", satuan="m³/m³",
                       batas=batas, tanggal=tanggal, lapisan=lapisan, grid=grid,
                       skala=dict(cmap="BrBG", min=0.05, max=0.5))
    print(f"{kunci}: {len(berkas)} tanggal, batas", [round(v, 3) for v in batas])

# ------------------------------------------------------------- 3. Kalbar HV
a, b = np.load("kalbar/k155_pra.npz"), np.load("kalbar/k155_pasca.npz")
x, y, epsg = a["x"], a["y"], int(a["epsg"])
hv0, hv1 = a["hv"], b["hv"]
sah = np.isfinite(hv0) & np.isfinite(hv1) & (hv0 > 0) & (hv1 > 0)
dB = np.where(sah, 10 * np.log10(np.where(sah, hv1, 1) / np.where(sah, hv0, 1)), np.nan).astype(np.float32)
# Topeng air. HV pra-kebakaran terbelah dua dengan bersih: air ~ -25 dB, darat
# ~ -12 dB, celah kosong di -22..-18 dB (histogram 1 Okt 2026). Ambang -20 dB.
# Dari citra PRA, bukan pasca: tanah yang terbakar jadi gundul bisa turun ke
# arah nilai air, dan topeng dari citra pasca akan membuang bekas bakar --
# persis yang ingin ditampilkan.
with np.errstate(divide="ignore", invalid="ignore"):
    dB[10 * np.log10(np.where(hv0 > 0, hv0, np.nan)) < -20] = np.nan
batas = batas_latlon(x, y, epsg)
g = proyeksikan(dB, x, y, epsg, batas, 900)
DATA["kalbar_hv"] = dict(judul="Perubahan hamburan balik HV, Kalimantan Barat", satuan="dB",
                         batas=batas, tanggal=[f"{a['tanggal']} → {b['tanggal']}"],
                         lapisan=[ke_png(g, "kalbar_hv.png", "RdYlGn", -6, 6)],
                         grid=[kasar(g, 90)], skala=dict(cmap="RdYlGn", min=-6, max=6))
print("kalbar_hv: batas", [round(v, 3) for v in batas])

# ------------------------------------------------------------- simpan
teks = "// Dibuat oleh bangun_data.py -- jangan disunting tangan.\nwindow.NISAR = " + \
       json.dumps(DATA, ensure_ascii=False, separators=(",", ":")) + ";\n"
(KELUAR / "data.js").write_text(teks, encoding="utf-8")
print(f"data.js {len(teks) // 1024} KB")
