# -*- coding: utf-8 -*-
"""Potong jendela Jakarta dari GUNW NISAR TANPA mengunduh 2,44 GB.

Berkas dibuka lewat permintaan Range (HTTP 206 terverifikasi), jadi hanya blok
yang benar-benar dibaca yang melintasi jaringan.

Keluaran: satu .npz per tanggal berisi fasa terbuka, koherensi, komponen
tersambung, pergeseran dalam cm, dan koordinat UTM-nya.

Konversi fasa -> pergeseran:
    d_los = -fasa * lambda / (4*pi)
NISAR L-band, frekuensi pusat 1257,5 MHz -> lambda = 0,2385 m.
Tanda negatif disengaja: fasa membesar = jarak ke satelit memendek = permukaan
NAIK, sehingga AMBLESAN bernilai negatif.

Proyeksi TIDAK diasumsikan; EPSG dibaca dari berkas (terbukti 32748, UTM 48S).
"""
from __future__ import annotations

import os
import netrc
import numpy as np

LAMBDA = 299_792_458.0 / 1_257_500_000.0          # meter
JKT = dict(lon0=106.6, lon1=107.1, lat0=-6.45, lat1=-6.00)
KELUAR = "nisar/data"
G = "science/LSAR/GUNW/grids/frequencyA"
U = G + "/unwrappedInterferogram"


def sesi():
    u, _, p = netrc.netrc().authenticators("urs.earthdata.nasa.gov")
    import asf_search as asf
    return asf.ASFSession().auth_with_creds(u, p)


def granul_turun(ses):
    import asf_search as asf
    poly = ("POLYGON(({0} {2},{1} {2},{1} {3},{0} {3},{0} {2}))"
            .format(JKT["lon0"], JKT["lon1"], JKT["lat0"], JKT["lat1"]))
    r = asf.search(platform=[asf.PLATFORM.NISAR], intersectsWith=poly,
                   processingLevel="GUNW", maxResults=100)
    return sorted((g for g in r if "_D_092_" in g.properties["sceneName"]),
                  key=lambda g: g.properties["startTime"])


def url_langsung(ses, g):
    """Selesaikan pengalihan berautentikasi -> URL CloudFront bertanda tangan."""
    nama = g.properties["sceneName"]
    u = g.properties["url"].rsplit("/", 1)[0] + "/" + nama + ".h5"
    r = ses.get(u, stream=True, timeout=180)
    r.close()
    return r.url


def buka(url):
    import fsspec, h5py
    fo = fsspec.open(url, mode="rb", block_size=4 * 1024 * 1024).open()
    return h5py.File(fo, "r"), fo


def main() -> None:
    os.makedirs(KELUAR, exist_ok=True)
    ses = sesi()
    gl = granul_turun(ses)
    print("granul jalur turun 092: {} tanggal".format(len(gl)))

    h, fo = buka(url_langsung(ses, gl[0]))
    epsg = int(h[U + "/projection"][()])
    x = h[U + "/xCoordinates"][:]
    y = h[U + "/yCoordinates"][:]
    h.close(); fo.close()

    print("EPSG dari berkas: {}".format(epsg))
    print("X {:,.0f} .. {:,.0f} m  ({} nilai, piksel {:.0f} m)"
          .format(x.min(), x.max(), len(x), abs(x[1] - x[0])))
    print("Y {:,.0f} .. {:,.0f} m  ({} nilai, piksel {:.0f} m)"
          .format(y.min(), y.max(), len(y), abs(y[1] - y[0])))

    from pyproj import Transformer
    tf = Transformer.from_crs("EPSG:4326", "EPSG:{}".format(epsg), always_xy=True)
    ex, ny_ = tf.transform([JKT["lon0"], JKT["lon1"]], [JKT["lat0"], JKT["lat1"]])
    x0, x1 = min(ex), max(ex)
    y0, y1 = min(ny_), max(ny_)
    print("kotak Jakarta dalam UTM: X {:,.0f}..{:,.0f}  Y {:,.0f}..{:,.0f}"
          .format(x0, x1, y0, y1))

    ix = np.flatnonzero((x >= x0) & (x <= x1))
    iy = np.flatnonzero((y >= y0) & (y <= y1))
    if len(ix) == 0 or len(iy) == 0:
        print("Kotak Jakarta di LUAR cakupan granul ini.")
        return
    print("jendela: {} baris x {} kolom = {:,} piksel ({:.1f} MB per lapisan)"
          .format(len(iy), len(ix), len(iy) * len(ix), len(iy) * len(ix) * 4 / 1e6))
    print()

    for g in gl:
        tgl = g.properties["startTime"][:10]
        out = "{}/jkt_{}.npz".format(KELUAR, tgl)
        if os.path.exists(out):
            print("  {}  sudah ada".format(tgl))
            continue
        h, fo = buka(url_langsung(ses, g))
        sl = (slice(iy[0], iy[-1] + 1), slice(ix[0], ix[-1] + 1))
        fasa = h[U + "/HH/unwrappedPhase"][sl]
        koh = h[U + "/HH/coherenceMagnitude"][sl]
        kom = h[U + "/HH/connectedComponents"][sl]
        h.close(); fo.close()

        d_cm = -fasa * LAMBDA / (4 * np.pi) * 100.0
        np.savez_compressed(out, fasa=fasa, koherensi=koh, komponen=kom,
                            d_cm=d_cm, x=x[ix], y=y[iy], epsg=epsg, tanggal=tgl)
        sah = np.isfinite(fasa) & (koh > 0.3)
        if sah.any():
            print("  {}  sah {:5.1%}  d_los {:+6.2f} .. {:+6.2f} cm  -> {}"
                  .format(tgl, sah.mean(), np.percentile(d_cm[sah], 2),
                          np.percentile(d_cm[sah], 98), out))
        else:
            print("  {}  TIDAK ADA piksel sah".format(tgl))


if __name__ == "__main__":
    main()
