# KasirKita Desktop

**KasirKita** adalah aplikasi kasir desktop untuk usaha kecil yang membutuhkan pencatatan produk, stok, transaksi tunai, dan laporan penjualan secara lokal di komputer Windows.

Dikembangkan oleh **The Choco Corporation**.

> **Status produk: dalam pengembangan, belum siap dijual.** Dokumentasi ini menjelaskan ruang lingkup dan fitur yang telah ada di source. Paket instalasi dan seluruh alur utama tetap harus melewati pemeriksaan rilis sebelum ditawarkan kepada pembeli.

## Ringkasan produk

- **Desktop-first:** dirancang untuk laptop dan komputer desktop; bukan aplikasi Android.
- **Offline-first:** alur kasir inti menggunakan database SQLite lokal dan tidak mensyaratkan akun, server, atau koneksi internet.
- **Data milik pengguna:** database disimpan di direktori data pengguna Windows, terpisah dari folder program.
- **Laporan lokal:** ekspor laporan dan struk ke format dokumen yang dapat dibuka di aplikasi lain.
- **Dukungan:** tautan bantuan membuka Choco AI di browser; pelanggan dapat menyampaikan masukan melalui kanal bantuan tersebut.

## Fitur yang tersedia di source

### Kasir dan transaksi
- Pencarian produk dan keranjang belanja.
- Transaksi tunai dengan validasi uang yang diterima dan perhitungan kembalian.
- Diskon nominal per transaksi dengan validasi agar tidak melebihi nilai keranjang.
- Penyimpanan snapshot nama dan harga produk pada transaksi.
- Pengurangan stok yang dilakukan bersama penyimpanan transaksi dalam satu operasi database.
- Input SKU manual atau scanner USB yang berperilaku seperti keyboard.

### Produk dan stok
- Menambah, mencari, mengedit, serta mengaktifkan atau menonaktifkan produk.
- SKU internal otomatis dengan pola seperti `KK-000001`.
- Penyesuaian stok masuk/keluar dengan alasan dan catatan pergerakan.
- Pencatatan harga modal per produk dan snapshot harga modal saat transaksi.
- Ekspor katalog produk ke CSV dan label barcode Code 128 berbasis SKU ke SVG.

### Riwayat dan laporan
- Riwayat transaksi dan detail transaksi tersimpan.
- Ekspor struk ke TXT dan PDF.
- Ringkasan penjualan menurut tanggal lokal komputer.
- Catatan retur yang mengembalikan stok, pencatatan pengeluaran operasional, serta ringkasan laba berdasarkan harga modal dan retur.
- Daftar stok menipis yang dapat diekspor ke CSV.
- Ekspor laporan CSV, workbook Excel `.xlsx`, dan PDF A4 lanskap.

### Pengaturan dan perlindungan data
- Pengaturan pajak opsional, nonaktif secara default, dengan tarif dan mode yang dikonfigurasi pengguna.
- Backup database serta validasi pemulihan dengan backup pengaman.
- Tutorial offline pada penggunaan pertama, dapat dilewati dan dibuka ulang.
- Log aplikasi lokal untuk membantu diagnosis masalah.

## Tahap implementasi

Source saat ini mencakup fitur kasir inti dan modul operasional berikut:
1. **Fitur inti:** kasir tunai, katalog produk, stok, riwayat transaksi, laporan dan ekspor, struk, pengaturan pajak, backup dan restore.
2. **Operasional toko:** diskon nominal, pencatatan retur dan pengembalian stok, pengeluaran operasional, harga modal per produk, ringkasan laba, barcode SKU, dan ekspor daftar stok menipis.
3. **Akun lokal dan data relasi:** login terpisah pemilik/pegawai, pendaftaran pemilik pertama, pengelolaan akun pegawai, pemulihan akun dengan NIK dan kode pemulihan satu kali, serta data pelanggan dan supplier.

Akun, pelanggan, supplier, retur, harga modal, dan pengeluaran disimpan pada SQLite lokal. NIK tidak disimpan sebagai teks biasa. Kata sandi diproses dengan PBKDF2-HMAC-SHA-256. Pemulihan akun pemilik memerlukan NIK dan kode pemulihan sekali pakai; kata sandi lama tidak pernah diekspor ke file. Fitur ini tidak bergantung pada Choco AI, Supabase, atau koneksi internet.

Deteksi perangkat berjalan saat aplikasi dibuka dan menampilkan versi Windows, arsitektur, jumlah prosesor logis, RAM yang terdeteksi, resolusi layar, dan profil penggunaan sumber daya. Ukuran jendela disesuaikan dengan ruang layar dan profil perangkat. Kompatibilitas OS tetap ditentukan dari pengujian build dan pemasangan aktual, bukan dari deteksi saja.

## Unduh installer Windows

Installer dibangun oleh workflow Windows dan dipublikasikan langsung ke repository, jadi tidak perlu membuka daftar artifact untuk mengambil ZIP:

[**Unduh KasirKita-Setup.exe**](https://github.com/chocoanakbaik/KasirKita/raw/refs/heads/main/installer-release/KasirKita-Setup.exe)

Checksum SHA-256: [KasirKita-Setup.sha256](https://raw.githubusercontent.com/chocoanakbaik/KasirKita/main/installer-release/KasirKita-Setup.sha256). File installer diperbarui ketika build Windows terbaru berhasil.

## Batasan yang perlu diketahui

- Metode pembayaran yang tersedia pada versi awal adalah tunai.
- Barcode saat ini mencari SKU internal, bukan nomor produk resmi GS1/GTIN.
- Pajak merupakan kalkulator yang dapat dikonfigurasi, bukan jaminan kepatuhan hukum atau perpajakan. Pengguna bertanggung jawab memverifikasi perlakuan pajak yang berlaku.
- Target kompatibilitas adalah Windows 10 dan Windows 11; Windows 8.1 dapat dicoba tetapi tetap belum terverifikasi pada perangkat fisik. Deteksi sistem operasi tidak menggantikan uji instalasi pada setiap versi Windows.
- Installer dan paket portable belum boleh dianggap sebagai rilis final sebelum build, instalasi, shortcut, uninstall, backup/pemulihan, dan alur UI diuji pada lingkungan Windows yang bersih.
- Belum ada klaim bahwa aplikasi bebas dari semua bug.

## Identitas dan dukungan

Nama produk: **KasirKita Desktop**  
Penerbit: **The Choco Corporation**  
Asisten bantuan dan kanal masukan: [Choco AI](https://choco-ai-platform.netlify.app/)

KasirKita dapat melakukan kesalahan. Pengguna tetap perlu memeriksa harga, stok, hasil transaksi, dan laporan. Buat backup secara berkala dan simpan salinannya di lokasi terpisah.

## Menjalankan dari source

Persyaratan: Python dengan Tkinter tersedia. Untuk membuat logo PNG dan ikon Windows dari sumber brand, pasang dependensi build lalu jalankan generator satu kali:

```powershell
py -m pip install -r requirements-build.txt
py scripts/generate_brand_assets.py
py -m kasirkita
```

Data aplikasi disimpan pada direktori data pengguna, bukan di samping source atau executable. Pada Windows, lokasi default menggunakan `%LOCALAPPDATA%\KasirKita`.

## Menjalankan pengujian

```powershell
py -m compileall -q kasirkita tests
py -m unittest discover -v
```

GitHub Actions menguji source pada Windows dan Ubuntu dengan Python 3.8 dan 3.12. Hasil CI bukan pengganti pengujian manual installer pada setiap versi Windows yang akan didukung.

## Dokumentasi pengembangan

- [Persyaratan Desktop v1](docs/REQUIREMENTS_DESKTOP_V1.md)
- [Autentikasi dan Pengelolaan Akun](docs/AUTHENTICATION_AND_ACCOUNT_MANAGEMENT.md)
- [Arsitektur Desktop v1](docs/ARCHITECTURE_DESKTOP_V1.md)
- [Panduan Pengguna Alpha](docs/PANDUAN_PENGGUNA_ALPHA.md)
- [Checklist Rilis](docs/RELEASE_CHECKLIST.md)

## Gerbang rilis

KasirKita baru dapat dipasarkan setelah seluruh pemeriksaan wajib pada [Checklist Rilis](docs/RELEASE_CHECKLIST.md) selesai dan bukti pengujiannya dicatat. Status README, source, workflow, dan paket distribusi harus tetap konsisten. Jangan mengiklankan sistem operasi, fitur, atau jaminan yang belum diverifikasi.
