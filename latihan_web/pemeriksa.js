// Pemeriksa otomatis untuk kerangka.html. Kamu TIDAK perlu membaca atau
// mengedit berkas ini. Ia memeriksa hasil TODO(kamu) satu per satu dan
// menampilkan kotak centang di pojok kiri bawah.
//
// Cara kerjanya (kalau penasaran): ia membaca variabel global yang kamu buat
// (TEMUAN, WARNA, peta), memeriksa lapisan di peta, lalu memanggil
// tampilkan() langsung. Selama memeriksa, peta.flyTo/setView/panTo diganti
// sementara supaya peta tidak bergerak, dan isi panel dikembalikan sesudahnya.
(function () {
  "use strict";

  const LANGKAH = [
    [0, "Data: enam temuan, kunci wajib lengkap"],
    [1, "Peta dibuat (variabel peta)"],
    [2, "Lapisan ubin terpasang"],
    [3, "Minimal satu titik di posisi yang benar"],
    [4, "Semua titik + warna + tooltip"],
    [5, "Titik bisa diklik"],
    [6, "Panel terisi + peta mendekat"],
    [7, "Gambar tampil di panel"],
    [8, "Legenda di pojok peta"],
    [9, "Grafik batang (penantang)"],
  ];

  const ada = (nama) => {
    try { return typeof eval(nama) !== "undefined"; } catch (e) { return false; }
  };
  const ambil = (nama) => eval(nama);

  // Pesan memuat teks seperti <script> atau <div class=...>; tanpa ini,
  // innerHTML membacanya sebagai tag sungguhan dan pesannya hilang.
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  function hexKeRgb(hex) {
    const h = hex.replace("#", "");
    const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
    return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
  }

  function periksa() {
    const hasil = {};            // nomor -> { ok: true|false|null, pesan }
    const set = (i, ok, pesan) => { hasil[i] = { ok, pesan: pesan || "" }; };

    // ---------------------------------------------------------------- 0 data
    let T = null, W = null;
    if (!ada("TEMUAN")) {
      set(0, false, "TEMUAN tidak terbaca. Biasanya <script>-mu mati karena galat ketik " +
                    "(koma hilang?). Buka konsol (F12 -> Console), lihat baris merahnya.");
    } else {
      T = ambil("TEMUAN"); W = ada("WARNA") ? ambil("WARNA") : {};
      const wajib = ["nama", "lat", "lon", "status", "metode", "angka"];
      let salah = "";
      for (const t of T) {
        const kurang = wajib.filter((k) => !(k in t));
        if (kurang.length) { salah = `"${t.nama || "?"}" tidak punya kunci: ${kurang.join(", ")}`; break; }
        if (!(t.status in W)) { salah = `"${t.nama}": status "${t.status}" tidak ada di WARNA`; break; }
        if (t.lat < -11 || t.lat > 6 || t.lon < 95 || t.lon > 141) {
          salah = `"${t.nama}": (${t.lat}, ${t.lon}) di luar Indonesia. Lintang/bujur tertukar?`; break;
        }
      }
      if (salah) set(0, false, salah);
      else if (T.length < 6) set(0, false, `Baru ${T.length} temuan, harusnya 6. Kerjakan TODO 0.`);
      else set(0, true, `${T.length} temuan`);
    }

    // ---------------------------------------------------------------- 1 peta
    const P = ada("peta") ? ambil("peta") : null;
    if (!P) set(1, false, "Variabel `peta` belum ada. TODO 1: const peta = L.map(...).setView(...)");
    else if (!(P instanceof L.Map)) set(1, false, "`peta` ada, tapi bukan peta Leaflet. Dibuat dengan L.map(\"peta\")?");
    else set(1, true);
    if (!hasil[1].ok) {
      for (let i = 2; i <= 9; i++) set(i, null, "menunggu langkah 1");
      return hasil;
    }

    // ---------------------------------------------------------------- 2 ubin
    const lapisan = [];
    P.eachLayer((l) => lapisan.push(l));
    const ubin = lapisan.filter((l) => l instanceof L.TileLayer);
    set(2, ubin.length > 0, ubin.length ? "" : "Belum ada L.tileLayer(...).addTo(peta). TODO 2.");

    // ---------------------------------------------------------------- 3-5 titik
    const titik = lapisan.filter((l) => typeof l.getLatLng === "function" && !(l instanceof L.Popup) &&
                                        !(l instanceof L.Tooltip));
    const dekat = (a, b) => Math.abs(a - b) < 1e-6;
    const pasang = [];           // [penanda, temuan]
    let tertukar = 0;
    for (const m of titik) {
      const ll = m.getLatLng();
      const t = T && T.find((x) => dekat(x.lat, ll.lat) && dekat(x.lon, ll.lng));
      if (t) pasang.push([m, t]);
      else if (T && T.find((x) => dekat(x.lat, ll.lng) && dekat(x.lon, ll.lat))) tertukar++;
    }
    if (tertukar) set(3, false, `${tertukar} titik memakai [bujur, lintang]. Leaflet minta [LINTANG, BUJUR].`);
    else if (!pasang.length) set(3, false, titik.length ? "Ada titik, tapi tidak di koordinat temuan mana pun."
                                                        : "Belum ada titik. TODO 3: L.circleMarker([lat, lon], {...}).addTo(peta)");
    else set(3, true);

    if (!hasil[3].ok) { set(4, null, "menunggu langkah 3"); set(5, null, "menunggu langkah 3"); }
    else {
      const nTemuan = T ? T.length : 0;
      const tanpaTooltip = pasang.filter(([m, t]) => !(m.getTooltip && m.getTooltip() &&
                                          String(m.getTooltip().getContent()).includes(t.nama)));
      const salahWarna = pasang.filter(([m, t]) => m.options && "color" in m.options &&
          ![m.options.color, m.options.fillColor].map((c) => String(c).toLowerCase())
             .includes(String(W[t.status]).toLowerCase()));
      if (pasang.length < nTemuan) set(4, false, `${pasang.length} dari ${nTemuan} titik. TODO 4: for (const t of TEMUAN) {...}`);
      else if (salahWarna.length) set(4, false, `Warna "${salahWarna[0][1].nama}" bukan WARNA[t.status].`);
      else if (tanpaTooltip.length) set(4, false, `"${tanpaTooltip[0][1].nama}" belum punya .bindTooltip(t.nama).`);
      else set(4, true);

      // Jangan pakai m.listens("click"): bindTooltip/bindPopup ikut memasang
      // pendengar klik bawaan Leaflet. Hitung hanya pendengar buatanmu.
      const klikSendiri = (m) => ((m._events && m._events.click) || [])
        .some((h) => h.fn !== m._openTooltip && h.fn !== m._openPopup);
      const tuli = pasang.filter(([m]) => !klikSendiri(m));
      set(5, !tuli.length, tuli.length
        ? 'Titik belum mendengarkan klik. TODO 5: .on("click", () => tampilkan(t)). Ingat "() =>".' : "");
    }

    // ---------------------------------------------------------------- 6,7,9 panel
    const panel = document.getElementById("panel");
    const asliPanel = panel.innerHTML;
    const asli = { flyTo: P.flyTo, setView: P.setView, panTo: P.panTo };
    let gerak = null;
    for (const k of Object.keys(asli)) P[k] = function (ll) { gerak = L.latLng(ll); return P; };

    const coba = (t) => {
      panel.innerHTML = ""; gerak = null;
      try { tampilkan(t); return null; } catch (e) { return e.message; }
    };
    try {
      if (!T || typeof tampilkan !== "function") {
        set(6, false, "Fungsi tampilkan(t) tidak ditemukan.");
      } else {
        const t0 = T.find((x) => x.gambar && x.grafik) || T[0];
        const galat = coba(t0);
        const teks = panel.textContent;
        if (galat) set(6, false, `tampilkan() galat: ${galat}`);
        else if (!teks.trim()) set(6, false, "Panel masih kosong. TODO 6: isi panel.innerHTML di tampilkan(t).");
        else if (!teks.includes(t0.nama) || !teks.includes(t0.angka))
          set(6, false, "Panel belum memuat nama DAN angka temuan.");
        else if (!gerak || !dekat(gerak.lat, t0.lat) || !dekat(gerak.lng, t0.lon))
          set(6, false, "Panel terisi, tapi peta belum mendekat: peta.flyTo([t.lat, t.lon], 8).");
        else {
          const bocor = T.find((t) => { coba(t); return panel.innerHTML.includes("undefined"); });
          set(6, !bocor, bocor ? `"${bocor.nama}" menampilkan "undefined": kunci opsional perlu ternary ? : "".` : "");
        }

        // 7 gambar
        if (!hasil[6].ok) set(7, null, "menunggu langkah 6");
        else {
          const tg = T.find((x) => x.gambar);
          coba(tg);
          const img = panel.querySelectorAll("img");
          const cap = panel.querySelectorAll("figcaption");
          const srcOk = [...img].every((im, i) => tg.gambar[i] && im.getAttribute("src") === tg.gambar[i].src);
          if (img.length !== tg.gambar.length)
            set(7, false, `"${tg.nama}" punya ${tg.gambar.length} gambar, panel menampilkan ${img.length}. TODO 7.`);
          else if (!srcOk) set(7, false, "Urutan/alamat gambar tidak sama dengan data.");
          else if (cap.length !== tg.gambar.length) set(7, false, "Gambar tampil, keterangannya (<figcaption>) belum.");
          else set(7, true);
        }

        // 9 grafik
        if (!hasil[6].ok) set(9, null, "menunggu langkah 6");
        else {
          const tf = T.find((x) => x.grafik);
          coba(tf);
          const baris = panel.querySelectorAll(".batang-baris");
          // Dibaca dari atribut style mentah: lebar negatif DITOLAK CSS (style.width
          // jadi kosong), padahal angkanya justru petunjuk paling berguna.
          const isi = [...panel.querySelectorAll(".batang-isi")].map((d) => {
            const m = /width\s*:\s*(-?[\d.]+)\s*%/.exec(d.getAttribute("style") || "");
            return m ? parseFloat(m[1]) : NaN;
          });
          const mutlak = tf.grafik.batang.map((b) => Math.abs(b.nilai));
          const harap = mutlak.map((v) => (v / Math.max(...mutlak)) * 100);
          if (baris.length !== tf.grafik.batang.length)
            set(9, false, `Butuh ${tf.grafik.batang.length} <div class="batang-baris">, ada ${baris.length}. TODO 9.`);
          else if (isi.some((w) => w < 0))
            set(9, false, `Lebar batang negatif (${isi.map((w) => w.toFixed(1) + "%").join(", ")}): ` +
                          "nilai σ-nya negatif, lebar harus positif. Lupa Math.abs?");
          else if (isi.length !== harap.length || isi.some((w, i) => !(Math.abs(w - harap[i]) < 0.5)))
            set(9, false, `Lebar batang ${isi.map((w) => (isNaN(w) ? "?" : w.toFixed(1) + "%")).join(", ")}; ` +
                          `harusnya ${harap.map((w) => w.toFixed(1) + "%").join(", ")}.`);
          else set(9, true);
        }
      }
    } finally {
      for (const k of Object.keys(asli)) P[k] = asli[k];
      panel.innerHTML = asliPanel;
    }

    // ---------------------------------------------------------------- 8 legenda
    const leg = document.querySelector("#peta .legenda");
    if (!leg) set(8, false, 'Belum ada kotak .legenda di peta. TODO 8: L.control({ position: "bottomright" }).');
    else {
      const warnaLeg = [...leg.querySelectorAll(".titik")].map((s) => getComputedStyle(s).backgroundColor);
      const perlu = Object.values(W).map(hexKeRgb);
      const kurang = perlu.filter((c) => !warnaLeg.includes(c));
      set(8, !kurang.length, kurang.length ? "Legenda ada, tapi warnanya belum sama dengan WARNA." : "");
    }
    return hasil;
  }

  // ------------------------------------------------------------------ tampilan
  function gambar(hasil) {
    let kotak = document.getElementById("pemeriksa");
    if (!kotak) {
      kotak = document.createElement("div");
      kotak.id = "pemeriksa";
      kotak.style.cssText =
        "position:fixed;left:12px;bottom:12px;z-index:2000;max-width:340px;background:var(--kartu,#fff);" +
        "color:var(--teks,#111);border:1px solid var(--garis,#ccc);border-radius:8px;padding:10px 12px;" +
        "font:13px/1.45 system-ui,sans-serif;box-shadow:0 2px 10px rgba(0,0,0,.25)";
      document.body.appendChild(kotak);
    }
    const nOk = LANGKAH.filter(([i]) => hasil[i] && hasil[i].ok).length;
    const pertamaGagal = LANGKAH.find(([i]) => hasil[i] && hasil[i].ok === false);
    const kecil = kotak.dataset.kecil === "1";
    const baris = LANGKAH.map(([i, judul]) => {
      const h = hasil[i] || { ok: null };
      const ikon = h.ok === true ? "✓" : h.ok === false ? "✗" : "·";
      const warna = h.ok === true ? "#1f7a4d" : h.ok === false ? "#b4532a" : "#9b9a94";
      return `<div><span style="color:${warna};font-weight:700;display:inline-block;width:16px">${ikon}</span>` +
             `${i}. ${judul}</div>`;
    }).join("");
    const saran = pertamaGagal
      ? `<div style="margin-top:6px;padding-top:6px;border-top:1px solid var(--garis,#ccc)">` +
        `<b>Berikutnya, langkah ${pertamaGagal[0]}:</b> ${esc(hasil[pertamaGagal[0]].pesan)}</div>`
      : `<div style="margin-top:6px"><b>Semua lulus.</b> Sekarang bandingkan dengan index.html.</div>`;
    kotak.innerHTML =
      `<div style="display:flex;justify-content:space-between;gap:8px;align-items:center">` +
      `<b>Pemeriksa ${nOk}/${LANGKAH.length}</b><span>` +
      `<button id="pemeriksa-ulang" style="font:inherit">periksa ulang</button> ` +
      `<button id="pemeriksa-kecil" style="font:inherit">${kecil ? "buka" : "kecilkan"}</button></span></div>` +
      (kecil ? "" : `<div style="margin-top:6px">${baris}</div>${saran}`);
    document.getElementById("pemeriksa-ulang").onclick = jalankan;
    document.getElementById("pemeriksa-kecil").onclick = () => {
      kotak.dataset.kecil = kecil ? "0" : "1"; gambar(hasil);
    };
  }

  function jalankan() {
    let hasil;
    try { hasil = periksa(); }
    catch (e) { hasil = { 0: { ok: false, pesan: "Pemeriksa sendiri galat: " + e.message } }; }
    gambar(hasil);
    for (const [i, judul] of LANGKAH) {
      const h = hasil[i] || { ok: null, pesan: "" };
      console.log(`[Pemeriksa] ${h.ok === true ? "LULUS" : h.ok === false ? "BELUM" : "-----"}  ${i}. ${judul}` +
                  (h.pesan ? `  (${h.pesan})` : ""));
    }
  }

  window.addEventListener("load", () => setTimeout(jalankan, 300));
})();
