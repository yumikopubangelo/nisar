"""Uji koherensi letusan Anak Krakatau dengan KONTROL PULAU TETANGGA.

Pertanyaan: koherensi di Anak Krakatau runtuh saat letusan 25 Agu - 6 Sep 2026.
Bagaimana kita tahu itu letusan, dan bukan hujan / ionosfer / orbit meleset?

Jawabannya rancangan, bukan argumen. Di bingkai yang SAMA ada tiga pulau lain
(Sertung, Panjang, Rakata). Mereka melewati atmosfer, orbit, dan pengolahan yang
persis sama. Kalau salah satu dari itu penyebabnya, mereka ikut runtuh.

Masukan: nisar/krakatau/{pra1..pra4,LETUSAN,pasca}.npz  (dari potong GUNW 010A/175)
         tiap berkas berisi  koh[y,x], x[], y[] (meter), epsg
Keluaran: tabel median koherensi per wilayah per selang + skor simpangan baku.

Penjelasan rumus dan jebakannya: docs/panduan_kode_nisar.md bagian 9.
"""
import numpy as np
from pyproj import Transformer

SELANG = ["pra1", "pra2", "pra3", "pra4", "LETUSAN", "pasca"]
LABEL = dict(zip(SELANG, ["26Jun-8Jul", "8-20Jul", "20Jul-13Agu",
                          "13-25Agu", "25Agu-6Sep", "6-18Sep"]))
# (nama, bujur, lintang, jari-jari km) -- tiga terakhir adalah KONTROL
PULAU = [("Anak Krakatau", 105.423, -6.102, 1.6),
         ("Sertung (BL)",  105.385, -6.090, 2.5),
         ("Panjang (TL)",  105.455, -6.090, 1.5),
         ("Rakata (S)",    105.435, -6.150, 2.5)]
PRA = ["pra1", "pra2", "pra3", "pra4"]


def muat(direktori="nisar/krakatau"):
    D = {k: np.load("{}/{}.npz".format(direktori, k)) for k in SELANG}
    d0 = D["pra1"]
    return D, d0["x"], d0["y"], int(d0["epsg"])


def topeng_darat(D, ambang=0.35):
    """Darat = koherensi dasar tinggi. HARUS dari selang PRA-letusan saja.

    Kalau selang letusan ikut dirata-rata, pulau yang koherensinya runtuh akan
    terbuang dari topengnya sendiri -- dan sinyal yang kita cari ikut hilang.
    Ini melingkar, dan mudah terjadi tanpa sadar.
    """
    dasar = np.mean([D[k]["koh"] for k in ("pra1", "pra2", "pra3")], axis=0)
    return dasar > ambang


def lingkaran(XX, YY, darat, tf, lon, lat, r_km):
    """Piksel darat di dalam lingkaran r_km dari (lon, lat).

    tf mengubah derajat -> meter UTM. Koordinat produk NISAR dalam METER,
    bukan derajat (jebakan 2), jadi jarak dihitung di ruang meter.
    """
    cx, cy = tf.transform(lon, lat)
    return darat & (((XX - cx) ** 2 + (YY - cy) ** 2) < (r_km * 1000.0) ** 2)


def main():
    D, x, y, epsg = muat()
    tf = Transformer.from_crs("EPSG:4326", "EPSG:{}".format(epsg), always_xy=True)
    XX, YY = np.meshgrid(x, y)
    darat = topeng_darat(D)

    wil = {n: lingkaran(XX, YY, darat, tf, lo, la, r) for n, lo, la, r in PULAU}

    print("{:<16}{:>8}".format("wilayah", "piksel")
          + "".join("{:>12}".format(LABEL[k]) for k in SELANG))
    print("-" * 104)
    for nama, m in wil.items():
        if m.sum() < 50:
            print("  {} terlalu sedikit piksel".format(nama))
            continue
        # MEDIAN, bukan mean: koherensi punya ekor piksel ~0 di tepi pantai dan
        # bayangan lereng, dan besar tarikannya berubah antar-tanggal.
        v = [np.median(D[k]["koh"][m]) for k in SELANG]
        print("{:<16}{:>8,}".format(nama, m.sum())
              + "".join("{:>12.4f}".format(a) for a in v))

    print("\nskor terhadap dasar masing-masing wilayah:")
    for nama, m in wil.items():
        if m.sum() < 50:
            continue
        b = np.array([np.median(D[k]["koh"][m]) for k in PRA])
        lt = np.median(D["LETUSAN"]["koh"][m])
        z = (lt - b.mean()) / max(b.std(ddof=1), 1e-9)
        print("  {:<16} dasar {:.4f}+-{:.4f}  letusan {:.4f}  -> {:+.1f} simpangan baku"
              .format(nama, b.mean(), b.std(ddof=1), lt, z))
    print("\nBacaan: selisih antara Krakatau dan ketiga tetangga tidak bisa")
    print("dijelaskan oleh apa pun yang dialami keempat pulau bersama-sama.")


if __name__ == "__main__":
    main()
