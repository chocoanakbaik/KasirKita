# KasirKita

KasirKita adalah aplikasi kasir (Point of Sale/POS) yang dikembangkan untuk dijual sebagai produk digital.

## Fokus Produk

Versi pertama adalah **KasirKita Desktop**, khusus laptop dan komputer desktop. Android dan platform lain tidak termasuk fokus versi pertama.

Aplikasi dirancang offline-first dengan database SQLite lokal. Server, akun online, dan layanan berbayar bukan persyaratan penggunaan.

## Prinsip Pengembangan

- Pengerjaan dilakukan bertahap, satu bagian pada satu waktu, dengan rincian dan hubungan antarmodul diperiksa sebelum melanjutkan.
- Target kualitas adalah tidak ada bug yang diketahui saat suatu bagian dinyatakan selesai. Setiap temuan harus dicatat, ditelusuri penyebabnya, diperbaiki, lalu diuji ulang.
- Algoritma bisnis dipisahkan dari UI dan akses database agar perhitungan tidak memiliki versi berbeda di setiap layar.
- Uang disimpan sebagai nilai integer rupiah; binary floating-point tidak boleh digunakan untuk total transaksi.
- Penyimpanan penjualan, item penjualan, pembayaran, dan perubahan stok harus dilakukan secara atomik.
- Pengujian tidak boleh diklaim telah dilakukan jika memang belum dijalankan. Status yang belum diuji harus dinyatakan belum terverifikasi.
- Penyelesaian tahap ditentukan oleh kriteria penerimaan dan hasil pengujian, bukan sekadar karena kode sudah ditulis.

## Dokumen Proyek

- [Persyaratan Desktop v1](docs/REQUIREMENTS_DESKTOP_V1.md)
- [Arsitektur Desktop v1](docs/ARCHITECTURE_DESKTOP_V1.md)

## Menjalankan Aplikasi dari Source

Dengan Python dan Tkinter terpasang, dari direktori utama repository jalankan:

```powershell
py -m kasirkita
```

Database lokal disimpan di folder data pengguna, bukan di samping source atau executable. Di Windows, lokasi default menggunakan folder Local AppData pengguna.

## Menjalankan Pengujian

```powershell
py -m compileall -q kasirkita tests
py -m unittest discover -v
```

GitHub Actions menjalankan kompilasi dan pengujian otomatis pada Windows dan Ubuntu dengan Python 3.8 serta 3.12. Workflow yang hijau membuktikan pengujian pada lingkungan tersebut, bukan otomatis membuktikan kompatibilitas pada setiap versi Windows.

## Status Implementasi

Sudah ada fondasi database SQLite, katalog produk, transaksi tunai awal, pengurangan stok atomik, riwayat transaksi dan detail struk, serta UI desktop awal untuk kasir dan pengelolaan produk. Status tiap bagian tetap mengikuti hasil pengujian yang benar-benar selesai.

**Aplikasi ini belum dinyatakan siap dijual.** Backup/restore, packaging installer, pengujian pada Windows 8.1 secara langsung, audit alur transaksi end-to-end, dan sejumlah fitur operasional masih perlu dikerjakan sebelum rilis.

## Pajak dan PPN

Pada implementasi saat ini, pajak belum diterapkan dan total transaksi dihitung tanpa PPN. Fitur pajak direncanakan opsional. Perilaku PPN, pembulatan, harga termasuk/tidak termasuk pajak, dan penyimpanan aturan pajak pada transaksi historis harus ditetapkan serta diuji sebelum fitur pajak diimplementasikan. Pengguna bertanggung jawab mengonfigurasi aplikasi sesuai status usaha dan ketentuan yang berlaku.

## Prinsip Kejujuran Status

Dokumentasi ini membedakan rancangan, implementasi, pengujian, dan rilis. Tidak ada fitur yang boleh disebut selesai, teruji, kompatibel, atau siap dijual tanpa bukti yang sesuai.
