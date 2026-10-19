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
- Penjualan, item penjualan, pembayaran, dan perubahan stok disimpan sebagai operasi atomik.
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

## Fitur yang Sudah Diimplementasikan

- UI desktop awal dengan tab Kasir, Produk, Riwayat Transaksi, dan Laporan.
- Katalog produk: tambah, cari, edit detail, dan aktifkan/nonaktifkan produk.
- Penyesuaian stok masuk/keluar dengan alasan dan catatan pergerakan stok.
- Transaksi tunai, validasi uang diterima dan kembalian, snapshot nama/harga produk, serta pengurangan stok atomik.
- Riwayat transaksi dan detail struk berdasarkan data yang tersimpan.
- Ringkasan penjualan berdasarkan tanggal lokal komputer.
- Backup database tervalidasi dan pemulihan dengan backup pengaman sebelum data aktif diganti.
- Database lokal SQLite dan log aplikasi lokal.

## Menjalankan Pengujian

```powershell
py -m compileall -q kasirkita tests
py -m unittest discover -v
```

GitHub Actions menjalankan kompilasi dan pengujian otomatis pada Windows dan Ubuntu dengan Python 3.8 serta 3.12. Workflow yang hijau membuktikan pengujian pada lingkungan tersebut, bukan otomatis membuktikan kompatibilitas pada setiap versi Windows.

## Status Rilis

**Aplikasi belum dinyatakan siap dijual.** Installer/package belum disiapkan dan diuji, kompatibilitas pada Windows 8.1 belum diverifikasi langsung, dan alur UI harus melewati pemeriksaan manual end-to-end sebelum rilis. Fitur yang sudah ada tetap dapat memiliki masalah yang belum ditemukan; statusnya mengikuti bukti pengujian terbaru.

## Pajak dan PPN

Pada implementasi saat ini, pajak belum diterapkan dan transaksi dihitung tanpa PPN. Fitur pajak direncanakan opsional. Perilaku PPN, pembulatan, harga termasuk/tidak termasuk pajak, dan penyimpanan aturan pajak pada transaksi historis harus ditetapkan serta diuji sebelum fitur pajak diimplementasikan. Aplikasi tidak boleh mengklaim kepatuhan pajak otomatis. Pengguna bertanggung jawab mengonfigurasi aplikasi sesuai status usaha dan ketentuan yang berlaku.

## Prinsip Kejujuran Status

Dokumentasi ini membedakan rancangan, implementasi, pengujian, dan rilis. Tidak ada fitur yang boleh disebut selesai, teruji, kompatibel, atau siap dijual tanpa bukti yang sesuai.
