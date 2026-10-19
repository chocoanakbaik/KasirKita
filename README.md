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
- [Panduan Pengguna Alpha](docs/PANDUAN_PENGGUNA_ALPHA.md)
- [Checklist Rilis](docs/RELEASE_CHECKLIST.md)

## Menjalankan Aplikasi dari Source

Dengan Python dan Tkinter terpasang, dari direktori utama repository jalankan:

```powershell
py -m kasirkita
```

Database lokal disimpan di folder data pengguna, bukan di samping source atau executable. Di Windows, lokasi default menggunakan folder Local AppData pengguna.

## Fitur yang Sudah Diimplementasikan

- UI desktop dengan tab Kasir, Produk, Riwayat Transaksi, Laporan, dan Pengaturan.
- Katalog produk: tambah, cari, edit detail, dan aktifkan/nonaktifkan produk.
- Penyesuaian stok masuk/keluar dengan alasan dan catatan pergerakan stok.
- Transaksi tunai dengan validasi uang diterima dan kembalian, snapshot nama/harga produk, dan pengurangan stok atomik.
- Pajak opsional dengan status nonaktif secara default, tarif yang dikonfigurasi pengguna, mode harga termasuk/tidak termasuk pajak, pembulatan integer, dan snapshot konfigurasi pajak pada transaksi.
- Riwayat transaksi dan detail struk berdasarkan data yang tersimpan.
- Ringkasan penjualan berdasarkan tanggal lokal komputer, dengan ekspor laporan CSV UTF-8 yang ramah Excel.
- Backup database tervalidasi dan pemulihan dengan backup pengaman sebelum data aktif diganti.
- Database lokal SQLite dan log aplikasi lokal.
- Pemberitahuan bahwa aplikasi dapat melakukan kesalahan, dengan tautan bantuan yang membuka platform Choco AI di browser bawaan. Logo merek ditampilkan bila Pillow tersedia; aplikasi tetap berjalan tanpa Pillow.

## Menjalankan Pengujian

```powershell
py -m compileall -q kasirkita tests
py -m unittest discover -v
```

GitHub Actions menjalankan kompilasi dan pengujian otomatis pada Windows dan Ubuntu dengan Python 3.8 serta 3.12. Workflow yang hijau membuktikan pengujian pada lingkungan tersebut, bukan otomatis membuktikan kompatibilitas pada setiap versi Windows.

## Status Rilis

**Aplikasi belum dinyatakan siap dijual.** Installer/package belum disiapkan dan diuji, kompatibilitas pada Windows 8.1 belum diverifikasi langsung, dan alur UI harus melewati pemeriksaan manual end-to-end sebelum rilis. Fitur yang sudah ada tetap dapat memiliki masalah yang belum ditemukan; statusnya mengikuti bukti pengujian terbaru.

## Pajak dan PPN

Pajak nonaktif secara default. Pengguna dapat mengaktifkan pajak, mengatur label, tarif, dan apakah harga yang dimasukkan sudah termasuk pajak atau belum. Tarif tidak diisi otomatis. Setiap transaksi menyimpan konfigurasi pajak yang digunakan saat transaksi dibuat, sehingga perubahan pengaturan tidak menulis ulang transaksi lama.

Perhitungan ini adalah alat bantu yang dapat dikonfigurasi, **bukan sertifikasi kepatuhan pajak**. Perlakuan PPN dapat bergantung pada status usaha, jenis barang/jasa, dasar pengenaan pajak, dan ketentuan yang berlaku. Pengguna harus memverifikasi tarif serta perlakuan pajaknya sebelum memakai fitur ini untuk transaksi nyata.

## Prinsip Kejujuran Status

Dokumentasi ini membedakan rancangan, implementasi, pengujian, dan rilis. Tidak ada fitur yang boleh disebut selesai, teruji, kompatibel, atau siap dijual tanpa bukti yang sesuai.
