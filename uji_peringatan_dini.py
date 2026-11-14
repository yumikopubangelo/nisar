# -*- coding: utf-8 -*-
"""Uji peringatan dini: apakah tanah yang AKAN terbakar sudah mengering lebih
cepat daripada tetangganya, SEBELUM api muncul?

Ditulis 3 Okt 2026. KRITERIA DI BAWAH DITULIS SEBELUM HASIL DILIHAT. Jangan
diubah setelah menjalankan skrip ini; kalau gagal, laporkan sebagai gagal.

PERTANYAAN
    Radar NISAR (SME2, kelembapan tanah 200 m) melihat tanda bahaya >= 12 hari
    sebelum titik api FIRMS pertama di sebuah piksel?

KENAPA PENGERINGAN, BUKAN TINGKAT
    Membandingkan tingkat kelembapan saja hanya menemukan "lahan kering lebih
    sering terbakar": gambut yang sudah dikeringkan bertahun-tahun memang
    selalu lebih kering, dan itu bukan peringatan dini. Yang diukur:
        pengeringan = SM(tanggal pra-api) - SM(24 Jun, dasar)
    Sifat tetap lokasi (gambut, drainase) terhapus oleh selisih ini.

RANCANGAN
    Piksel TERBAKAR : piksel SME2 yang memuat >= 1 titik panas FIRMS. F = tanggal
                      titik panas PERTAMA di piksel itu.
    Tanggal pra-api : pengamatan SME2 terakhir yang <= F - 12 hari, dan sesudah
                      24 Jun (tanggal dasar). Piksel tanpa tanggal seperti itu
                      dibuang.
    KONTROL         : piksel yang (a) tutupan lahannya SAMA, (b) berjarak > 1 km
                      dari titik panas mana pun sepanjang Jun-Sep, (c) berada
                      dalam 20 km dari klaster terbakarnya, dan diukur pada
                      tanggal pra-api yang SAMA.
    Klaster         : sel 0,1 derajat x tanggal pra-api x tutupan lahan.
                      Selisih dihitung per klaster: rata-rata terbakar - rata-rata
                      kontrol. Klaster, bukan piksel, karena piksel bertetangga
                      tidak saling bebas (api datang berkelompok).
    Ketidakpastian  : bootstrap 2.000 kali atas KLASTER, CI 95%.

KRITERIA LULUS (semuanya harus terpenuhi)
    K1  rata-rata selisih pengeringan (terbakar - kontrol) <= -0,02 m3/m3
    K2  CI 95% bootstrap seluruhnya di bawah 0
    K3  >= 20 klaster

PEMERIKSAAN PIPA (bukan kriteria, tapi WAJIB mendekati nol supaya hasil sah)
    Plasebo : ganti piksel terbakar dengan piksel acak yang TIDAK pernah
              terbakar (tutupan lahan dan sel yang sama), jalankan pipa yang
              sama persis. Selisihnya harus ~0. Kalau tidak, pipanya bias dan
              hasil utama tak bisa dipercaya, apa pun angkanya.

DILAPORKAN TAPI BUKAN KRITERIA
    Selisih TINGKAT pada 24 Jun: seberapa "kering dari sananya" lokasi yang
    terbakar. Ini menunjukkan seberapa besar perangkap yang dihindari.
"""
import glob
from datetime import date, timedelta

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.ndimage import binary_dilation

RNG = np.random.default_rng(2026)
JEDA = 12                                   # hari minimum sebelum api pertama
BUFFER_KM, CINCIN_KM = 1.0, 20.0

# ------------------------------------------------------------------ data SME2
berkas = sorted(glob.glob("sme2_155/sm_*.npz"))
d0 = np.load(berkas[0])
x, y, epsg = d0["x"], d0["y"], int(d0["epsg"])
lc = d0["lc"]
dx = abs(x[1] - x[0])
TGL = [date.fromisoformat(str(np.load(f)["tanggal"])) for f in berkas]
SM = []
for f in berkas:
    d = np.load(f)
    sm = d["sm"].astype(np.float64)
    sm[(sm < 0) | (d["wf"] > 0.5)] = np.nan             # isian -9999 & badan air
    SM.append(sm)
SM = np.array(SM)                                       # [tanggal, baris, kolom]
dasar = SM[0]
print(f"SME2: {len(TGL)} tanggal {TGL[0]}..{TGL[-1]}, piksel {dx:.0f} m, EPSG {epsg}")

# ------------------------------------------------------------------ FIRMS -> piksel
f = pd.read_csv("kalbar/firms.csv")
fx, fy = Transformer.from_crs(4326, epsg, always_xy=True).transform(f.longitude.values, f.latitude.values)
ix = np.rint((fx - x[0]) / (x[1] - x[0])).astype(int)
iy = np.rint((fy - y[0]) / (y[1] - y[0])).astype(int)     # y turun: pembagi negatif
ok = (ix >= 0) & (ix < len(x)) & (iy >= 0) & (iy < len(y))
f = f[ok].assign(ix=ix[ok], iy=iy[ok], tgl=pd.to_datetime(f.acq_date[ok]).dt.date)
print(f"titik panas di dalam bingkai SME2: {len(f):,}")

pernah_api = np.zeros(lc.shape, bool)
pernah_api[f.iy, f.ix] = True
r_buf = int(np.ceil(BUFFER_KM * 1000 / dx))
dekat_api = binary_dilation(pernah_api, iterations=r_buf)   # termasuk piksel api itu sendiri
pertama = f.groupby(["iy", "ix"]).tgl.min()

# lintang/bujur tiap piksel terbakar, untuk sel 0,1 derajat
ke_ll = Transformer.from_crs(epsg, 4326, always_xy=True)


def indeks_pra(F):
    """Indeks SME2 terakhir yang <= F - JEDA dan sesudah tanggal dasar."""
    batas = F - timedelta(days=JEDA)
    cocok = [i for i, t in enumerate(TGL) if t <= batas and i > 0]
    return cocok[-1] if cocok else None


bakar = []
for (r, c), F in pertama.items():
    i = indeks_pra(F)
    if i is None or not np.isfinite(dasar[r, c]) or not np.isfinite(SM[i, r, c]):
        continue
    lon, lat = ke_ll.transform(x[c], y[r])
    bakar.append(dict(r=r, c=c, i=i, lc=int(lc[r, c]), sel=(int(lat // 0.1), int(lon // 0.1)),
                      kering=SM[i, r, c] - dasar[r, c], tingkat0=dasar[r, c]))
bakar = pd.DataFrame(bakar)
print(f"piksel terbakar dengan pengamatan >= {JEDA} hari sebelum api: {len(bakar):,}")
print("  menurut tanggal pra-api:", bakar.i.map(lambda i: str(TGL[i])).value_counts().sort_index().to_dict())

# ------------------------------------------------------------------ pipa klaster
r_cin = int(np.ceil(CINCIN_KM * 1000 / dx))
boleh_kontrol = ~dekat_api & np.isfinite(dasar)


def selisih_per_klaster(kelompok):
    """kelompok: DataFrame piksel 'terbakar' (asli atau plasebo). -> DataFrame per klaster."""
    keluar = []
    for (sel, i, l), g in kelompok.groupby(["sel", "i", "lc"]):
        r0, r1 = max(g.r.min() - r_cin, 0), min(g.r.max() + r_cin + 1, lc.shape[0])
        c0, c1 = max(g.c.min() - r_cin, 0), min(g.c.max() + r_cin + 1, lc.shape[1])
        m = boleh_kontrol[r0:r1, c0:c1] & (lc[r0:r1, c0:c1] == l) & np.isfinite(SM[i, r0:r1, c0:c1])
        if m.sum() < 30:                        # kontrol terlalu sedikit -> klaster dibuang
            continue
        k_kering = (SM[i, r0:r1, c0:c1] - dasar[r0:r1, c0:c1])[m]
        k_tingkat = dasar[r0:r1, c0:c1][m]
        keluar.append(dict(sel=sel, i=i, lc=l, n_bakar=len(g), n_kontrol=int(m.sum()),
                           d_kering=g.kering.mean() - k_kering.mean(),
                           d_tingkat0=g.tingkat0.mean() - k_tingkat.mean()))
    return pd.DataFrame(keluar)


def bootstrap(v, n=2000):
    v = np.asarray(v)
    rata = np.array([RNG.choice(v, len(v)).mean() for _ in range(n)])
    return v.mean(), np.percentile(rata, 2.5), np.percentile(rata, 97.5)


K = selisih_per_klaster(bakar)

# ------------------------------------------------------------------ plasebo
# Untuk setiap piksel terbakar, ambil satu piksel ACAK yang tak pernah dekat api,
# tutupan lahan sama, dalam sel 0,1 derajat yang sama -> pipa yang sama persis.
ll_r, ll_c = np.nonzero(boleh_kontrol)
plasebo = []
for (sel, l), g in bakar.groupby(["sel", "lc"]):
    rr, cc = g.r.values, g.c.values
    m = ((ll_r >= rr.min() - r_cin // 4) & (ll_r <= rr.max() + r_cin // 4) &
         (ll_c >= cc.min() - r_cin // 4) & (ll_c <= cc.max() + r_cin // 4) & (lc[ll_r, ll_c] == l))
    calon = np.nonzero(m)[0]
    if len(calon) < len(g):
        continue
    pilih = RNG.choice(calon, len(g), replace=False)
    for (_, b), j in zip(g.iterrows(), pilih):
        r, c = ll_r[j], ll_c[j]
        if np.isfinite(SM[b.i, r, c]):
            plasebo.append(dict(r=r, c=c, i=b.i, lc=l, sel=sel,
                                kering=SM[b.i, r, c] - dasar[r, c], tingkat0=dasar[r, c]))
P = selisih_per_klaster(pd.DataFrame(plasebo))

# ------------------------------------------------------------------ laporan
print("\n" + "=" * 70)
m, lo, hi = bootstrap(K.d_kering)
pm, plo, phi = bootstrap(P.d_kering)
tm, tlo, thi = bootstrap(K.d_tingkat0)
print(f"klaster: {len(K)}  (piksel terbakar {K.n_bakar.sum():,}, median kontrol/klaster "
      f"{int(K.n_kontrol.median()):,})")
print(f"\nPENGERINGAN, terbakar - kontrol  : {m:+.4f} m3/m3   CI95 [{lo:+.4f}, {hi:+.4f}]")
print(f"PLASEBO (piksel tak terbakar)    : {pm:+.4f} m3/m3   CI95 [{plo:+.4f}, {phi:+.4f}]   "
      f"({len(P)} klaster)")
print(f"tingkat pada 24 Jun (bukan kriteria): {tm:+.4f}   CI95 [{tlo:+.4f}, {thi:+.4f}]")

print("\nper tanggal pra-api:")
for i, g in K.groupby("i"):
    a, b_, c_ = bootstrap(g.d_kering) if len(g) > 2 else (g.d_kering.mean(), np.nan, np.nan)
    print(f"  {TGL[i]}  (api pertama >= {JEDA} hari kemudian)  {len(g):>3} klaster  "
          f"{a:+.4f}  CI95 [{b_:+.4f}, {c_:+.4f}]")

k1, k2, k3 = m <= -0.02, hi < 0, len(K) >= 20
pipa_sah = plo <= 0 <= phi or abs(pm) < 0.005
print("\n" + "=" * 70)
print(f"K1 rata-rata <= -0,02      : {'LULUS' if k1 else 'gagal'}  ({m:+.4f})")
print(f"K2 CI95 seluruhnya < 0     : {'LULUS' if k2 else 'gagal'}  (batas atas {hi:+.4f})")
print(f"K3 >= 20 klaster           : {'LULUS' if k3 else 'gagal'}  ({len(K)})")
print(f"pipa sah (plasebo ~ 0)     : {'ya' if pipa_sah else 'TIDAK -- hasil utama tak bisa dipercaya'}"
      f"  ({pm:+.4f})")
print("\nVONIS:", "PERINGATAN DINI TERBUKTI" if (k1 and k2 and k3 and pipa_sah) else "TIDAK LULUS")
