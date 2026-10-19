# Panduan Pengguna — KasirKita Desktop (Alpha)

Dokumen ini menjelaskan perilaku aplikasi yang sudah tersedia pada source saat ini. Aplikasi masih dalam tahap pengembangan dan belum dinyatakan siap untuk operasional atau dijual.

## 1. Menjalankan aplikasi

Saat aplikasi pertama kali berjalan pada instalasi yang belum memiliki status tutorial, KasirKita membuka panduan interaktif otomatis. Ikuti tombol **Lanjut** dan **Kembali**, atau pilih **Lewati**. Statusnya disimpan di database lokal; tutorial tidak muncul otomatis lagi setelah selesai atau dilewati. Pilih **Panduan / Tutorial** di bagian bawah jendela untuk membukanya kembali kapan saja. Jika database aplikasi dihapus atau di-reset, status tutorial ikut hilang.

1. Pastikan Python dan Tkinter terpasang.
2. Buka terminal di direktori utama repository.
3. Jalankan `py -m kasirkita`.
4. Database dibuat pada direktori data pengguna. Jangan menghapus atau memindahkan file database ketika aplikasi sedang berjalan.

## 2. Menambahkan produk

Pada tab **Produk**, tombol **Ekspor katalog CSV** menyimpan hasil katalog yang sedang ditampilkan (termasuk filter pencarian aktif) ke CSV dengan pemisah titik koma dan encoding UTF-8 BOM agar lebih mudah dibuka di aplikasi spreadsheet.

1. Buka tab **Produk**.
2. Pilih **Tambah produk**.
3. Isi SKU, nama, harga rupiah, dan stok awal.
4. SKU dinormalisasi menjadi huruf kapital dan tidak boleh duplikat.
5. Harga harus berupa bilangan bulat rupiah; masukkan 25000 atau 25.000.
6. Gunakan **Edit detail** untuk mengubah SKU, nama, atau harga. Stok tidak diubah melalui form detail.

Produk yang sudah dipakai dalam transaksi tidak dihapus dari histori. Gunakan status nonaktif agar produk tidak dapat dipilih untuk transaksi baru.

## 3. Penyesuaian stok

1. Pilih produk pada tab **Produk**.
2. Tekan **Penyesuaian stok**.
3. Pilih penambahan atau pengurangan.
4. Masukkan jumlah unit dan alasan yang jelas.
5. Simpan. Sistem mencatat pergerakan stok dalam database.

Pengurangan stok yang membuat stok negatif ditolak. Penjualan juga mengurangi stok dalam transaksi database yang sama dengan pencatatan penjualan.

## 4. Memproses penjualan tunai

1. Buka tab **Kasir**.
2. Cari dan pilih produk.
3. Masukkan kuantitas lalu tekan **Tambah ke keranjang**.
4. Periksa subtotal, pajak, dan total.
5. Masukkan nominal uang yang diterima, lalu pilih **Proses pembayaran**.
6. Periksa nomor struk dan kembalian pada konfirmasi hasil.

Sebelum menyimpan penjualan, aplikasi membaca ulang harga dan stok dari database. Jika stok tidak cukup, produk tidak aktif, atau uang tidak cukup, transaksi ditolak. Jika salah satu langkah penyimpanan gagal, seluruh perubahan transaksi dan stok harus dibatalkan.

## 5. Pengaturan pajak

1. Buka tab **Pengaturan**.
2. Pajak dalam keadaan nonaktif secara default.
3. Untuk menggunakannya, aktifkan opsi pajak, isi label (misalnya PPN), masukkan tarif, lalu pilih apakah harga yang dimasukkan sudah termasuk pajak atau belum.
4. Tarif dapat ditulis seperti 11, 11,5, atau 11,25. Maksimal dua angka desimal.
5. Simpan pengaturan. Perubahan berlaku untuk transaksi baru.

Jika mode **Belum termasuk pajak** dipilih, pajak ditambahkan pada subtotal. Jika mode **Sudah termasuk pajak** dipilih, pajak dihitung sebagai bagian dari harga yang dimasukkan. Perhitungan menggunakan rupiah bulat dan pembulatan half-up.

**Penting:** tarif tidak diisi otomatis dan fitur ini tidak menjamin kepatuhan terhadap aturan PPN. Pastikan status usaha, dasar pengenaan, jenis transaksi, tarif, dan perlakuan pajak sesuai ketentuan yang berlaku sebelum dipakai untuk transaksi nyata.

## 6. Riwayat transaksi dan laporan

- Tab **Riwayat transaksi** menampilkan transaksi tersimpan. Pilih transaksi lalu buka detail untuk melihat snapshot nama produk, harga, subtotal, pajak, total, dan pembayaran. Dari jendela detail, pilih **Simpan struk TXT** untuk mengekspor struk UTF-8 yang dapat dibuka atau dicetak melalui aplikasi lain.
- Tab **Laporan** merangkum transaksi selesai dan unit terjual untuk rentang tanggal yang dimasukkan. Tanggal mengikuti zona waktu lokal komputer.
- Mengubah harga atau nama produk tidak boleh mengubah snapshot pada transaksi lama.

## 7. Backup dan pemulihan

### Membuat backup

1. Buka tab **Riwayat transaksi**.
2. Pilih **Buat backup**.
3. Simpan file database backup pada lokasi yang aman. Simpan salinan terpisah jika data penting.

### Memulihkan backup

1. Pilih **Pulihkan backup** dan tentukan file backup.
2. Konfirmasi bahwa data saat ini akan diganti.
3. Pilih lokasi untuk menyimpan backup data saat ini sebelum pemulihan.
4. Pemulihan dilanjutkan hanya jika file backup dapat divalidasi.

Jangan menghapus backup sebelum memastikan data hasil pemulihan benar. Untuk penggunaan penting, simpan salinan backup pada media lain yang tidak selalu terhubung ke komputer.

## 8. Batasan versi alpha

- Pembayaran yang tersedia saat ini adalah tunai.
- Belum ada installer resmi.
- Kompatibilitas pada Windows 8.1 harus diuji langsung sebelum dinyatakan didukung.
- Pembatalan/refund, pengaturan identitas usaha pada struk, dan prosedur rilis masih memerlukan pengembangan dan verifikasi.
- Jalankan pengujian otomatis sebelum menggabungkan perubahan source.
