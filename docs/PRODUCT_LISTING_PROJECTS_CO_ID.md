# Draft listing penjualan digital — KasirKita Desktop

> **Status: draf internal, jangan diunggah sebagai produk berbayar sebelum checklist rilis wajib selesai.** Dokumen ini menyiapkan materi listing. CI hijau dan keberadaan installer belum membuktikan pemasangan, uninstall, pemulihan database, dan alur UI sudah lolos uji manual di Windows bersih. Repository publik tidak menyediakan installer permanen lagi. Artefak GitHub Actions dari repo publik tetap dapat diakses publik dan bukan penyimpanan rahasia; bila source/build perlu dirahasiakan, pindahkan distribusi komersial ke repository privat sebelum rilis.

## Judul produk

KasirKita Desktop — Aplikasi Kasir Offline Windows, Stok, Retur, dan Laporan

## Deskripsi singkat

Aplikasi kasir desktop untuk Windows dengan database lokal. Catat transaksi tunai, kelola produk dan stok, lihat riwayat, catat retur serta pengeluaran toko, dan ekspor laporan ke CSV, Excel, atau PDF. Dirancang untuk pemilik usaha kecil yang ingin menyimpan data operasional di komputer sendiri tanpa bergantung pada koneksi internet untuk alur kasir utama.

## Deskripsi lengkap

KasirKita Desktop membantu usaha kecil mencatat penjualan dan persediaan secara lokal di komputer Windows.

Fitur utama:
- Transaksi tunai dengan keranjang, diskon nominal, pemeriksaan pembayaran, dan hitung kembalian.
- Katalog produk, SKU internal, pengaturan stok, dan riwayat pergerakan stok.
- Riwayat transaksi beserta detail dan ekspor struk TXT/PDF.
- Laporan penjualan dan ekspor CSV, Excel (.xlsx), serta PDF.
- Pencatatan pelanggan dan supplier.
- Retur penjualan, pengeluaran operasional, harga modal, ringkasan laba, dan stok menipis.
- Akun lokal pemilik/pegawai menggunakan ID login pilihan pengguna; tidak memerlukan NIK.
- Database SQLite lokal, backup, dan pemulihan.
- Tidak memerlukan langganan server atau koneksi internet untuk alur kasir inti.

KasirKita dibuat oleh The Choco Studios dan berfokus pada alur kerja desktop/offline. Pendaftaran akun menggunakan ID login lokal, bukan NIK, sehingga aplikasi tidak perlu mengumpulkan nomor identitas kependudukan. Database usaha tersimpan di komputer pengguna; pengguna bertanggung jawab menjaga akses Windows serta membuat backup di lokasi terpisah.

## Batasan yang perlu disampaikan kepada pembeli

- Hanya Windows desktop/laptop; bukan aplikasi Android atau iOS.
- Metode pembayaran versi ini adalah tunai.
- Belum menyediakan sinkronisasi cloud atau akses multi-perangkat.
- Tidak menyediakan pembayaran QRIS/transfer terintegrasi, piutang, atau pencetakan struk thermal langsung pada versi ini.
- SKU dan label Code 128 adalah kode internal, bukan pengganti nomor GTIN/GS1 resmi.
- Pajak nonaktif secara default dan tarif dikonfigurasi oleh pengguna; aplikasi tidak menjamin kepatuhan pajak.
- Target kompatibilitas Windows 10/11, tetapi dukungan harus dinyatakan hanya setelah pemasangan dan pengujian pada OS tersebut terbukti. Windows 8.1 belum terverifikasi.
- Jangan menyatakan produk bebas bug atau siap operasional sebelum checklist rilis menyertakan bukti uji manual.

## Isi paket yang direncanakan

1. `KasirKita-Setup.exe` — installer Windows.
2. `KasirKita-Setup.sha256` — checksum untuk memeriksa integritas installer.
3. Panduan pengguna berbahasa Indonesia.
4. Ringkasan perubahan versi dan catatan batasan.
5. Informasi kontak dukungan.

Jangan menyertakan database produksi atau data pribadi nyata. Bila menyertakan database demo, gunakan hanya data fiktif.

## Persyaratan sistem

Persyaratan minimum CPU, RAM, resolusi, dan ruang disk belum boleh dipublikasikan sebagai angka sebelum diuji pada installer rilis. Target OS yang direncanakan adalah Windows 10/11 64-bit. Catat hasil pengujian di `docs/RELEASE_CHECKLIST.md` sebelum menerbitkan klaim kompatibilitas.

## Rencana harga awal untuk diuji

Hipotesis harga peluncuran: **Rp39.000–Rp49.000** untuk lisensi penggunaan satu usaha pada satu komputer, dengan ketentuan penggunaan akhir yang jelas. Ini hanya titik awal untuk pengujian pasar, bukan harga final. Karena terdapat alternatif kasir gratis, penjualan perlu menonjolkan ekspor laporan, operasional offline lokal, pengelolaan retur/pengeluaran, serta biaya satu kali yang transparan.

FAQ Seller Projects.co.id menyatakan fee produk digital sebesar 20%; sebelum menetapkan harga, periksa kembali aturan serta biaya yang berlaku saat listing dibuat. Pada fee 20%, harga Rp39.000 menyisakan Rp31.200 sebelum biaya lain, dan Rp49.000 menyisakan Rp39.200. Sumber: https://projects.co.id/public/pages/faq_seller

## Syarat sebelum publish

- Semua tes otomatis berhasil pada branch yang akan dirilis.
- Build installer dan paket portable berhasil dari source yang sama.
- Uji manual Windows bersih meliputi instalasi, shortcut, login, transaksi, laporan, backup/restore, pembaruan, dan uninstall.
- Periksa checksum dan pastikan paket berisi panduan pengguna, bukan dokumen internal alpha.
- Tentukan lisensi penggunaan, kebijakan update, cara menghubungi dukungan, dan penanganan bug.
- Ambil screenshot langsung dari aplikasi yang berjalan. Jangan memakai mockup yang mengesankan fitur belum ada.
- Pastikan versi yang diunggah cocok dengan versi yang diuji dan catatan perubahan.

## Alternatif untuk listing apabila harga perlu diuji

Bila calon pembeli menganggap harga aplikasi terlalu tinggi dibanding pilihan gratis, jangan langsung menambah fitur acak. Uji dulu kebutuhan segmen yang benar-benar ingin menggunakan aplikasi kasir Windows lokal dan memerlukan ekspor laporan. Gunakan pertanyaan calon pembeli sebagai data untuk memutuskan fitur berikutnya.
