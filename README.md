# KasirKita

KasirKita adalah aplikasi kasir (Point of Sale/POS) yang dikembangkan untuk dijual sebagai produk digital.

## Fokus Produk

Versi pertama adalah **KasirKita Desktop**, khusus laptop dan komputer desktop. Android dan platform lain tidak termasuk fokus versi pertama.

Aplikasi dirancang offline-first dengan database lokal. Server, akun online, dan layanan berbayar tidak menjadi persyaratan penggunaan.

## Prinsip Pengembangan

- Pengerjaan dilakukan bertahap, satu bagian pada satu waktu, dengan rincian dan hubungan antarmodul diperiksa sebelum melanjutkan.
- Target kualitas adalah tidak ada bug yang diketahui saat suatu bagian dinyatakan selesai. Setiap temuan harus dicatat, ditelusuri penyebabnya, diperbaiki, lalu diuji ulang.
- Algoritma bisnis dipisahkan dari UI dan akses database agar perhitungan tidak memiliki versi yang berbeda di setiap layar.
- Uang disimpan sebagai nilai integer rupiah; binary floating-point tidak boleh digunakan untuk total transaksi.
- Transaksi penjualan dan perubahan stok harus dirancang sebagai operasi atomik agar kegagalan tidak meninggalkan data setengah tersimpan.
- Pengujian tidak boleh diklaim telah dilakukan jika memang belum dijalankan. Status yang belum diuji harus dinyatakan belum terverifikasi.
- Penyelesaian tahap ditentukan oleh kriteria penerimaan dan hasil pengujian, bukan sekadar karena kode sudah ditulis.

## Dokumen Proyek

- [Persyaratan Desktop v1](docs/REQUIREMENTS_DESKTOP_V1.md)
- [Arsitektur Desktop v1](docs/ARCHITECTURE_DESKTOP_V1.md)

## Menjalankan Pengujian

Dengan Python terpasang, jalankan dari direktori utama repository:

```powershell
py -m unittest discover -v
```

Workflow GitHub Actions juga disiapkan untuk menjalankan pengujian pada Windows dan Ubuntu dengan Python 3.10 serta 3.12. Hasil kompatibilitas hanya boleh disimpulkan dari workflow yang benar-benar selesai.

## Status Implementasi

Fondasi awal database SQLite dan pengujian integritas database sudah ditambahkan. Ini **belum merupakan aplikasi kasir yang siap digunakan atau dijual**. Katalog produk, layanan transaksi, stok, laporan, antarmuka, backup/restore, packaging, dan pemeriksaan kompatibilitas masih harus dikembangkan dan diuji secara bertahap.

## Pajak dan PPN

Fitur pajak direncanakan opsional. Perilaku PPN, pembulatan, harga termasuk/tidak termasuk pajak, dan penyimpanan aturan pajak pada transaksi historis harus ditetapkan sebelum fitur pajak diimplementasikan. Pengguna bertanggung jawab mengonfigurasi aplikasi sesuai status usaha dan ketentuan yang berlaku.

## Prinsip Kejujuran Status

Dokumentasi ini membedakan rancangan, implementasi, pengujian, dan rilis. Tidak ada fitur yang boleh disebut selesai, teruji, kompatibel, atau siap dijual tanpa bukti yang sesuai.
