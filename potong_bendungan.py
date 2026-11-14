# -*- coding: utf-8 -*-
"""Potong jendela tiga bendungan Citarum dari GUNW NISAR tanpa mengunduh penuh.

Jatiluhur, Cirata, Saguling -- ketiganya SELALU dalam satu bingkai (terverifikasi
16 dari 16 granul), sehingga atmosfer, orbit, dan pengolahannya identik. Itu yang
membuat kontrol antar-bendungan mungkin, persis seperti pulau tetangga di Krakatau.

Dua geometri diambil:
    jalur 018 MENURUN (D_092)   6 interferogram
    jalur 010 MENAIK  (A_174)   6 interferogram
Dua arah pandang memungkinkan pemisahan gerak tegak dari gerak timur-barat.

Ionosfer DIKURANGI, bukan ditambah (terverifikasi di Jakarta: simpangan 19,63 ->
3,40 cm bila dikurangi, memburuk ke 39,67 bila ditambah).

Keluaran: nisar/bendungan/<jalur>_<tgl1>_<tgl2>.npz
"""
from __future__ import annotations
import os, netrc, sys
import numpy as np

LAMBDA = 299_792_458.0 / 1_257_500_000.0
KOTAK = dict(lon0=107.25, lon1=107.55, lat0=-7.00, lat1=-6.45)
BEND = {"Jatiluhur": (107.390, -6.530),
        "Cirata":    (107.370, -6.700),
        "Saguling":  (107.370, -6.910)}
JALUR = {"D018": "_018_D_092_", "A010": "_010_A_174_"}
KELUAR = "nisar/bendungan"
G = "science/LSAR/GUNW/grids/frequencyA"
U = G + "/unwrappedInterferogram"


def sesi():
    u, _, p = netrc.netrc().authenticators("urs.earthdata.nasa.gov")
    import asf_search as asf
    return asf.ASFSession().auth_with_creds(u, p)


def cari(ses):
    import asf_search as asf
    r = asf.search(platform=[asf.PLATFORM.NISAR],
                   intersectsWith="POINT(107.370 -6.700)",     # Cirata, di tengah
                   processingLevel="GUNW", maxResults=120)
    out = {}
    for tag, pola in JALUR.items():
        out[tag] = sorted((g for g in r if pola in g.properties["sceneName"]),
                          key=lambda g: g.properties["startTime"])
    return out


def url_langsung(ses, g):
    nama = g.properties["sceneName"]
    u = g.properties["url"].rsplit("/", 1)[0] + "/" + nama + ".h5"
    rr = ses.get(u, stream=True, timeout=180); rr.close()
    return rr.url


def buka(url):
    import fsspec, h5py
    fo = fsspec.open(url, mode="rb", block_size=4 * 1024 * 1024).open()
    return h5py.File(fo, "r"), fo


def tanggal(nama):
    bag = [b for b in nama.split("_") if len(b) == 15 and b[8] == "T"]
    return (bag[0][:8], bag[2][:8]) if len(bag) >= 3 else ("?", "?")


def main():
    os.makedirs(KELUAR, exist_ok=True)
    ses = sesi()
    gl = cari(ses)
    for t, v in gl.items():
        print("{}: {} interferogram".format(t, len(v)))

    g0 = gl["D018"][0]
    h, fo = buka(url_langsung(ses, g0))
    print("\nisi {}/HH :".format(U))
    for k in h[U + "/HH"]:
        d = h[U + "/HH/" + k]
        print("   {:<28} {}".format(k, getattr(d, "shape", "")))
    epsg = int(h[U + "/projection"][()])
    x = h[U + "/xCoordinates"][:]; y = h[U + "/yCoordinates"][:]
    h.close(); fo.close()
    print("EPSG {}  piksel {:.0f} m  y menurun: {}".format(
        epsg, abs(x[1] - x[0]), y[0] > y[-1]))

    from pyproj import Transformer
    tf = Transformer.from_crs("EPSG:4326", "EPSG:{}".format(epsg), always_xy=True)
    ex, ny_ = tf.transform([KOTAK["lon0"], KOTAK["lon1"]], [KOTAK["lat0"], KOTAK["lat1"]])
    ix = np.flatnonzero((x >= min(ex)) & (x <= max(ex)))
    iy = np.flatnonzero((y >= min(ny_)) & (y <= max(ny_)))
    print("jendela {} x {} = {:,} piksel".format(len(iy), len(ix), len(iy) * len(ix)))
    for nama, (lo, la) in BEND.items():
        cx, cy = tf.transform(lo, la)
        print("   {:<10} di dalam jendela: {}".format(
            nama, bool(x[ix].min() <= cx <= x[ix].max()
                       and y[iy].min() <= cy <= y[iy].max())))
    print()

    for tag, lst in gl.items():
        for g in lst:
            t1, t2 = tanggal(g.properties["sceneName"])
            out = "{}/{}_{}_{}.npz".format(KELUAR, tag, t1, t2)
            if os.path.exists(out):
                print("  {} {}->{}  sudah ada".format(tag, t1, t2)); continue
            h, fo = buka(url_langsung(ses, g))
            sl = (slice(iy[0], iy[-1] + 1), slice(ix[0], ix[-1] + 1))
            gr = h[U + "/HH"]
            fasa = gr["unwrappedPhase"][sl]
            koh = gr["coherenceMagnitude"][sl]
            kom = gr["connectedComponents"][sl]
            iono = gr["ionospherePhaseScreen"][sl] if "ionospherePhaseScreen" in gr else None
            h.close(); fo.close()
            bersih = fasa if iono is None else (fasa - iono)     # DIKURANGI
            d_cm = -bersih * LAMBDA / (4 * np.pi) * 100.0
            np.savez_compressed(out, fasa=fasa, koherensi=koh, komponen=kom,
                                iono=(np.zeros(1) if iono is None else iono),
                                d_cm=d_cm, x=x[ix], y=y[iy], epsg=epsg,
                                tgl1=t1, tgl2=t2, jalur=tag)
            sah = np.isfinite(d_cm) & (koh > 0.3)
            print("  {} {}->{}  sah {:5.1%}  d {:+6.2f}..{:+6.2f} cm  iono:{}"
                  .format(tag, t1, t2, sah.mean(),
                          np.percentile(d_cm[sah], 2) if sah.any() else np.nan,
                          np.percentile(d_cm[sah], 98) if sah.any() else np.nan,
                          "ada" if iono is not None else "TIDAK ADA"))


if __name__ == "__main__":
    main()
