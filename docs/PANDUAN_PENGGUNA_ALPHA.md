# Panduan Pengguna — KasirKita Desktop (Alpha)

Dokumen ini menjelaskan perilaku aplikasi yang sudah tersedia pada source saat ini. Aplikasi masih dalam tahap pengembangan dan belum dinyatakan siap untuk operasional atau dijual.

## 1. Menjalankan aplikasi

Saat aplikasi pertama kali berjalan pada instalasi yang belum memiliki status tutorial, KasirKita membuka panduan interaktif otomatis. Ikuti tombol **Lanjut** dan **Kembali**, atau pilih **Lewati**. Statusnya disimpan di database lokal; tutorial tidak muncul otomatis lagi setelah selesai atau dilewati. Pilih **Panduan / Tutorial** di bagian bawah jendela untuk membukanya kembali kapan saja. Jika database aplikasi dihapus atau di-reset, status tutorial ikut hilang.

1. Pastikan Python dan Tkinter terpasang.
2. Buka terminal di direktori utama repository.
3. Jalankan `py -m kasirkita`.
4. Database dibuat pada direktori data pengguna. Jangan menghapus atau memindahkan file database ketika aplikasi sedang berjalan.

## 2. Login pemilik dan pegawai

Pada awal instalasi, pilih **Daftar akun pemilik pertama**. Isi nama, ID login 4–32 karakter, kata sandi minimal 10 karakter, lalu simpan kode pemulihan satu kali di tempat aman di luar komputer. Pendaftaran awal otomatis ditutup setelah akun pemilik dibuat.

Saat aplikasi dibuka berikutnya, pilih jalur **Login sebagai Pemilik** atau **Login sebagai Pegawai**. Jalur tersebut terpisah; akun pemilik tidak dapat masuk lewat formulir pegawai dan sebaliknya. Pemilik dapat membuka **Akun Pegawai** untuk membuat akun pegawai, menonaktifkan akun, dan mengatur ulang kata sandi pegawai.

Pemulihan kata sandi pemilik memerlukan ID login dan kode pemulihan sekali pakai, kemudian menetapkan kata sandi baru. ID login saja tidak cukup. Kode pemulihan disimpan di luar aplikasi dan tidak dapat ditampilkan ulang setelah pendaftaran. Kata sandi lama tidak pernah diekspor.\n\nUntuk database yang dibuat oleh build lama, ID login awal tetap berupa angka 16 digit yang sebelumnya digunakan. Migrasi tidak menghapus akun atau mengubah kata sandinya.

## 3. Menambahkan produk

Pada tab **Produk**, tombol **Ekspor katalog CSV** menyimpan hasil katalog yang sedang ditampilkan (termasuk filter pencarian aktif) ke CSV dengan pemisah titik koma dan encoding UTF-8 BOM agar lebih mudah dibuka di aplikasi spreadsheet.

1. Buka tab **Produk**.
2. Pilih **Tambah produk**.
3. Isi SKU, nama, harga rupiah, dan stok awal.
4. SKU dinormalisasi menjadi huruf kapital dan tidak boleh duplikat.
5. Harga harus berupa bilangan bulat rupiah; masukkan 25000 atau 25.000.
6. Gunakan **Edit detail** untuk mengubah SKU, nama, atau harga. Stok tidak diubah melalui form detail.

Produk yang sudah dipakai dalam transaksi tidak dihapus dari histori. Gunakan status nonaktif agar produk tidak dapat dipilih untuk transaksi baru.

## 4. Input kode pada kasir (uji barcode keyboard)

Di halaman Kasir tersedia kolom **Barcode / SKU**. Ketik SKU produk yang sudah terdaftar lalu tekan Enter, atau gunakan scanner USB yang berperilaku seperti keyboard dan mengirim Enter setelah kode. Produk aktif akan masuk ke keranjang; pemindaian berulang menambah jumlah sesuai kolom Jumlah. Kode tidak dikenal akan menampilkan peringatan. Tanpa scanner, pengujian tetap dapat dilakukan dengan mengetik SKU secara manual.

Saat ini nilai yang dicari adalah SKU produk, bukan kolom barcode pabrikan yang terpisah. Pada formulir produk baru, tombol **Buat kode otomatis** akan memilih SKU internal `KK-000001` dan seterusnya yang belum digunakan. Kode internal tidak sama dengan GTIN resmi GS1; jangan mengklaimnya sebagai identitas resmi perdagangan global. Kolom barcode pabrikan terpisah belum tersedia. Untuk membuat label, pilih produk di katalog lalu tekan **Buat label barcode SVG**. Hasilnya adalah gambar vektor Code 128 berdasarkan SKU, bukan GTIN resmi. Cetak pada ukuran yang menjaga garis tetap jelas, lalu uji pemindaian dengan perangkat yang mendukung Code 128.

## 5. Penyesuaian stok

1. Pilih produk pada tab **Produk**.
2. Tekan **Penyesuaian stok**.
3. Pilih penambahan atau pengurangan.
4. Masukkan jumlah unit dan alasan yang jelas.
5. Simpan. Sistem mencatat pergerakan stok dalam database.

Pengurangan stok yang membuat stok negatif ditolak. Penjualan juga mengurangi stok dalam transaksi database yang sama dengan pencatatan penjualan.

## 6. Memproses penjualan tunai

1. Buka tab **Kasir**.
2. Cari dan pilih produk.
3. Masukkan kuantitas lalu tekan **Tambah ke keranjang**.
4. Periksa subtotal, pajak, dan total.
5. Masukkan nominal uang yang diterima, lalu pilih **Proses pembayaran**.
6. Periksa nomor struk dan kembalian pada konfirmasi hasil.
7. Pada detail transaksi, struk dapat disimpan sebagai TXT atau PDF. File diekspor dari data transaksi yang tersimpan; ekspor tidak mengubah transaksi.

Sebelum menyimpan penjualan, aplikasi membaca ulang harga dan stok dari database. Jika stok tidak cukup, produk tidak aktif, atau uang tidak cukup, transaksi ditolak. Jika salah satu langkah penyimpanan gagal, seluruh perubahan transaksi dan stok harus dibatalkan.

## 7. Pengaturan pajak

1. Buka tab **Pengaturan**.
2. Pajak dalam keadaan nonaktif secara default.
3. Untuk menggunakannya, aktifkan opsi pajak, isi label (misalnya PPN), masukkan tarif, lalu pilih apakah harga yang dimasukkan sudah termasuk pajak atau belum.
4. Tarif dapat ditulis seperti 11, 11,5, atau 11,25. Maksimal dua angka desimal.
5. Simpan pengaturan. Perubahan berlaku untuk transaksi baru.

Jika mode **Belum termasuk pajak** dipilih, pajak ditambahkan pada subtotal. Jika mode **Sudah termasuk pajak** dipilih, pajak dihitung sebagai bagian dari harga yang dimasukkan. Perhitungan menggunakan rupiah bulat dan pembulatan half-up.

**Penting:** tarif tidak diisi otomatis dan fitur ini tidak menjamin kepatuhan terhadap aturan PPN. Pastikan status usaha, dasar pengenaan, jenis transaksi, tarif, dan perlakuan pajak sesuai ketentuan yang berlaku sebelum dipakai untuk transaksi nyata.

## 8. Riwayat transaksi dan laporan

- Tab **Riwayat transaksi** menampilkan transaksi tersimpan. Pilih transaksi lalu buka detail untuk melihat snapshot nama produk, harga, subtotal, pajak, total, dan pembayaran. Dari jendela detail, pilih **Simpan struk TXT** untuk mengekspor struk UTF-8 yang dapat dibuka atau dicetak melalui aplikasi lain.
- Tab **Laporan** merangkum transaksi selesai dan unit terjual untuk rentang tanggal yang dimasukkan. Tanggal mengikuti zona waktu lokal komputer.
- Mengubah harga atau nama produk tidak boleh mengubah snapshot pada transaksi lama.

## 9. Backup dan pemulihan

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

## 10. Pelanggan, supplier, dan operasional

- Tab **Pelanggan & Supplier** menyimpan, mencari, mengubah, menonaktifkan, dan mengaktifkan kembali catatan pelanggan maupun supplier.
- Tab **Operasional → Harga Modal & Stok** mengatur harga modal per produk dan mengekspor daftar stok menipis. Harga modal yang tersimpan pada transaksi adalah snapshot, sehingga perubahan harga modal berikutnya tidak mengubah transaksi lama.
- Tab **Operasional → Pengeluaran** mencatat biaya toko dengan kategori, tanggal, nominal, dan catatan. Catatan yang salah dapat dibatalkan tanpa menghapus jejaknya.
- Tab **Operasional → Retur** mencari transaksi selesai, memilih item dan jumlah yang diretur, lalu mencatat pengembalian stok. Retur berlebih ditolak.
- Tab **Operasional → Laba** merangkum pendapatan barang, harga modal barang terjual, laba kotor, pengeluaran operasional, dan laba setelah pengeluaran pada rentang tanggal yang dipilih.
- Pada tab **Kasir**, tombol Diskon mengatur diskon nominal untuk transaksi yang sedang disiapkan. Diskon di atas nilai keranjang ditolak dan kembali ke nol setelah transaksi berhasil.

## 11. Informasi perangkat

Tab **Perangkat** menampilkan versi Windows yang terdeteksi, arsitektur, jumlah prosesor logis, RAM, resolusi layar, dan profil aplikasi. KasirKita menyesuaikan ukuran jendela berdasarkan ruang layar dan profil perangkat. Informasi tersebut diproses lokal dan tidak dikirim ke server.

## 12. Unduhan dan batasan versi alpha

- Pembayaran yang tersedia saat ini adalah tunai.
- Installer Windows dibangun oleh GitHub Actions dan dipublikasikan langsung sebagai [KasirKita-Setup.exe](https://github.com/chocoanakbaik/KasirKita/raw/refs/heads/main/installer-release/KasirKita-Setup.exe). Build terbaru harus berhasil sebelum file dianggap versi terkini.
- Target kompatibilitas adalah Windows 10 dan Windows 11; Windows 8.1 belum diverifikasi di perangkat fisik.
- Alur retur, akun, dan modul operasional harus melewati uji manual pada installer Windows sebelum dipakai untuk operasional nyata.
- Jalankan pengujian otomatis sebelum menggabungkan perubahan source.
