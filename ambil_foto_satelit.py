# -*- coding: utf-8 -*-
"""Foto satelit warna asli dari NASA Worldview (Snapshots API), tanpa kunci.

Untuk website: gambar yang dilihat mata (asap, abu letusan), pelengkap gambar
radar yang menjadi BUKTI. Lapisan: VIIRS (NOAA-20, SNPP) dan MODIS (Terra,
Aqua) -- satelit berbeda melintas jam berbeda, jadi kalau satu tertutup awan
yang lain kadang cerah.

Hasil WAJIB dilihat sebelum dipakai: "server menjawab 200" tidak berarti
gambarnya berisi sesuatu (awan penuh, petak hitam di luar lintasan).
"""
import sys
import urllib.request
from pathlib import Path

import pandas as pd

KELUAR = Path("latihan_web/gambar")
KELUAR.mkdir(parents=True, exist_ok=True)
API = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
LAPISAN = {
    "viirs_n20": "VIIRS_NOAA20_CorrectedReflectance_TrueColor",
    "viirs_snpp": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
    "modis_terra": "MODIS_Terra_CorrectedReflectance_TrueColor",
    "modis_aqua": "MODIS_Aqua_CorrectedReflectance_TrueColor",
}
TITIK_API = "VIIRS_NOAA20_Thermal_Anomalies_375m_All"   # titik api di atas citra


def ambil(nama, tanggal, bbox, lapisan, api=False, lebar=640):
    """bbox = (lat_min, lon_min, lat_max, lon_max) -- urutan EPSG:4326 WMS 1.3."""
    lap = LAPISAN[lapisan] + (f",{TITIK_API}" if api else "")
    s, w, n, e = bbox
    tinggi = round(lebar * (n - s) / (e - w))
    url = (f"{API}?REQUEST=GetSnapshot&TIME={tanggal}&BBOX={s},{w},{n},{e}"
           f"&CRS=EPSG:4326&LAYERS={lap}&FORMAT=image/jpeg&WIDTH={lebar}&HEIGHT={tinggi}")
    p = KELUAR / f"{nama}_{tanggal}_{lapisan}.jpg"
    p.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    print(f"  {p.name}  {p.stat().st_size // 1024} KB")
    return p


if __name__ == "__main__":
    tugas = sys.argv[1] if len(sys.argv) > 1 else "semua"

    if tugas in ("tanggal", "semua"):
        f = pd.read_csv("kalbar/firms.csv")
        s = f[f.latitude.between(0.3, 0.75) & f.longitude.between(108.8, 109.25)]
        print("titik panas dekat lokasi karhutla, tanggal teratas:")
        print(s.acq_date.value_counts().head(6).to_string())

    if tugas == "krakatau":
        for t in sys.argv[2:]:
            for lap in LAPISAN:
                ambil("krakatau", t, (-6.35, 105.15, -5.85, 105.70), lap)

    if tugas == "kalbar":
        for t in sys.argv[2:]:
            for lap in ("viirs_n20", "modis_terra", "modis_aqua"):
                ambil("kalbar", t, (0.15, 108.70, 0.95, 109.50), lap, api=True)
