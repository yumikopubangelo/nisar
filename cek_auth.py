# -*- coding: utf-8 -*-
"""Uji autentikasi Earthdata + intip struktur HDF5 GUNW TANPA mengunduh penuh.

Berkas GUNW 2,48 GB. Kita cuma butuh beberapa lapisan di atas Jakarta, jadi
langkah pertama adalah membuktikan HDF5-nya bisa dibaca sebagian lewat jaringan.
Kalau bisa, seluruh proyek jadi ringan. Kalau tidak, kita terpaksa mengunduh
dan memotong lokal.

Tidak ada kredensial yang tercetak di sini.
"""
from __future__ import annotations

import netrc
import sys

MESIN = "urs.earthdata.nasa.gov"
JKT = "POLYGON((106.6 -6.4,107.0 -6.4,107.0 -6.0,106.6 -6.0,106.6 -6.4))"


def kredensial():
    try:
        u, _, p = netrc.netrc().authenticators(MESIN)
    except Exception as e:
        sys.exit(f"GAGAL baca ~/.netrc: {type(e).__name__}: {e}")
    if not u or u.startswith("GANTI_DENGAN"):
        sys.exit("~/.netrc masih berisi placeholder. Isi dulu username/password.")
    return u, p


def main() -> None:
    u, p = kredensial()
    print(f"kredensial terbaca untuk pengguna: {u[:3]}***  (panjang sandi {len(p)})")

    import asf_search as asf
    ses = asf.ASFSession().auth_with_creds(u, p)
    print("sesi Earthdata: OK")

    r = asf.search(platform=[asf.PLATFORM.NISAR], intersectsWith=JKT,
                   processingLevel="GUNW", maxResults=100)
    # jalur TURUN 092 saja -> deret waktu satu geometri
    turun = sorted((g for g in r if "_D_092_" in g.properties["sceneName"]),
                   key=lambda g: g.properties["startTime"])
    print(f"\nGUNW jalur turun 092: {len(turun)} tanggal")
    for g in turun:
        print(f"   {g.properties['startTime'][:10]}")

    g = turun[0]
    url = g.properties["url"]
    print(f"\nmencoba baca sebagian lewat jaringan:\n  {url[:96]}...")

    import fsspec, h5py
    try:
        f = fsspec.open(url, mode="rb", client_kwargs={},
                        headers=None)  # ASF pakai redirect ber-auth
        with f as fo, h5py.File(fo, "r") as h:
            print("\nBERHASIL dibaca sebagian. Struktur tingkat atas:")
            h.visit(lambda n: print("   ", n) if n.count("/") < 3 else None)
    except Exception as e:
        print(f"\nbaca-sebagian GAGAL: {type(e).__name__}: {str(e)[:200]}")
        print("-> jatuh ke rencana B: unduh satu granul lalu potong lokal.")
        print(f"   ukuran: {sum(v['bytes'] for v in g.properties['bytes'].values())/1e9:.2f} GB")


if __name__ == "__main__":
    main()
