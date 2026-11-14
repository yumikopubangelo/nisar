# -*- coding: utf-8 -*-
"""Uji deformasi tiga bendungan Citarum dengan DUA KONTROL yang saling bebas.

Kontrol 1 -- TITIK ACAK: 300 piksel berkoherensi >0,8 di bingkai yang sama diukur
dengan prosedur yang persis sama. Sebaran hasilnya adalah lantai derau. Sebuah
bendungan baru berarti kalau ia keluar dari sebaran itu.

Kontrol 2 -- DUA GEOMETRI: jalur menurun (D018) dan menaik (A010) melihat titik
tanah yang sama dari arah berbeda, pada hari berbeda, sehingga atmosfernya bebas
satu sama lain. Gerak TEGAK muncul dengan tanda SAMA di keduanya; gerak
TIMUR-BARAT dengan tanda BERLAWANAN dan magnitudo sebanding. Yang muncul hanya di
satu jalur bukan gerakan.

Kontrol 2 itu yang menyelamatkan analisis ini: Cirata memberi +3,54 simpangan baku
di jalur menurun -- terlihat seperti temuan -- dan jalur menaik tidak
mengkonfirmasinya sama sekali.

ACUAN LOKAL: tiap titik dikurangi median cincin 0,24-3,2 km di sekitarnya. Ini
membuang atmosfer dan efek topografi yang bergelombang panjang, dan menyisakan
gerak struktur relatif terhadap tanah tepat di sekelilingnya. Penting di sini
sebab medannya pegunungan, tidak seperti Jakarta yang datar.

Jalankan setelah nisar/potong_bendungan.py.
"""
from __future__ import annotations
import glob
import numpy as np
from pyproj import Transformer

BEND = {"Jatiluhur": (107.390, -6.530),
        "Cirata":    (107.370, -6.700),
        "Saguling":  (107.370, -6.910)}
R_CARI = 25          # +-2 km: koordinat nominal bisa jatuh di air
R_DALAM, R_LUAR = 3, 40


def muat(tag):
    fs = sorted(glob.glob("nisar/bendungan/{}_*.npz".format(tag)))
    return fs, [np.load(f) for f in fs]


def lokal(d, iy, ix, yy, xx):
    """Nilai titik dikurangi median cincin di sekitarnya, dalam komponen yang sama.

    Komponen tersambung WAJIB dicocokkan: tiap komponen punya acuan pembukaan
    fasa sendiri, jadi membandingkan lintas komponen membandingkan dua nol yang
    berbeda.
    """
    kom, koh, v = d["komponen"], d["koherensi"], d["d_cm"]
    k0 = kom[iy, ix]
    if k0 <= 0 or not np.isfinite(v[iy, ix]):
        return np.nan
    rr = np.hypot(yy - iy, xx - ix)
    m = (rr > R_DALAM) & (rr <= R_LUAR) & (kom == k0) & (koh > 0.4) & np.isfinite(v)
    if m.sum() < 200:
        return np.nan
    return np.nanmedian(v[iy - 1:iy + 2, ix - 1:ix + 2]) - np.nanmedian(v[m])


def titik_koheren(D, x, y, epsg):
    """Koordinat nominal bendungan sering jatuh di PERMUKAAN WADUK (koherensi ~0,1).
    Struktur betonnya justru pemantul paling stabil, jadi cari piksel paling
    koheren dalam radius 2 km yang sah di SEMUA selang."""
    tf = Transformer.from_crs("EPSG:4326", "EPSG:{}".format(epsg), always_xy=True)
    kb = np.nanmean([d["koherensi"] for d in D], 0)
    ok = np.all([d["komponen"] > 0 for d in D], 0)
    out = {}
    for n, (lo, la) in BEND.items():
        cx, cy = tf.transform(lo, la)
        iy = int(np.abs(y - cy).argmin())
        ix = int(np.abs(x - cx).argmin())
        sl = (slice(iy - R_CARI, iy + R_CARI + 1), slice(ix - R_CARI, ix + R_CARI + 1))
        b = kb[sl].copy(); b[~ok[sl]] = np.nan
        j = np.unravel_index(np.nanargmax(b), b.shape)
        out[n] = (iy - R_CARI + j[0], ix - R_CARI + j[1])
    return out


def lantai(D, yy, xx, H, W, n=300, benih=7):
    kb = np.nanmean([d["koherensi"] for d in D], 0)
    k0 = D[0]["komponen"]
    s = np.argwhere((kb > 0.8) & (k0 > 0) & (yy > 45) & (yy < H - 45)
                    & (xx > 45) & (xx < W - 45))
    r = np.random.default_rng(benih)
    p = s[r.choice(len(s), min(n, len(s)), replace=False)]
    a = [np.nansum([lokal(d, int(i), int(j), yy, xx) for d in D]) for i, j in p]
    return np.array([v for v in a if np.isfinite(v)])


def main():
    _, Dd = muat("D018")
    _, Da = muat("A010")
    x, y, epsg = Dd[0]["x"], Dd[0]["y"], int(Dd[0]["epsg"])
    assert np.array_equal(x, Da[0]["x"]) and np.array_equal(y, Da[0]["y"]), \
        "grid kedua jalur berbeda -- petakan lewat METER, jangan lewat indeks"
    H, W = Dd[0]["koherensi"].shape
    yy, xx = np.mgrid[0:H, 0:W]

    ad, aa = lantai(Dd, yy, xx, H, W), lantai(Da, yy, xx, H, W)
    print("lantai derau 84 hari:  menurun {:.2f} cm  |  menaik {:.2f} cm"
          .format(ad.std(ddof=1), aa.std(ddof=1)))
    print("(ini BATAS DETEKSI -- gerak di bawahnya tidak bisa dibedakan dari derau)\n")

    T = titik_koheren(Dd, x, y, epsg)
    print("{:<11}{:>22}{:>24}".format("", "MENURUN (D018)", "MENAIK (A010)"))
    for n, (iy, ix) in T.items():
        sd = np.nansum([lokal(d, iy, ix, yy, xx) for d in Dd])
        sa = np.nansum([lokal(d, iy, ix, yy, xx) for d in Da])
        zd = (sd - np.median(ad)) / ad.std(ddof=1)
        za = (sa - np.median(aa)) / aa.std(ddof=1)
        setuju = "KONSISTEN" if abs(zd) < 2 and abs(za) < 2 else "TIDAK KONFIRM"
        print("{:<11}{:+8.2f} cm ({:+5.2f} sb){:+10.2f} cm ({:+5.2f} sb)   {}"
              .format(n, sd, zd, sa, za, setuju))
    print("\nSatu geometri saja TIDAK CUKUP. Cirata memberi +3,5 simpangan baku di")
    print("jalur menurun dan tidak terkonfirmasi di jalur menaik.")


if __name__ == "__main__":
    main()
