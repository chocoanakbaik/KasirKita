# Panduan Pengguna KasirKita Desktop

Panduan ini ditujukan untuk pengguna yang menjalankan KasirKita dari installer Windows. Nama dan tata letak beberapa tombol dapat berbeda pada versi mendatang; ikuti informasi versi pada judul jendela aplikasi.

## 1. Membuka aplikasi dan menyiapkan akun

1. Selesaikan pemasangan KasirKita, lalu buka dari menu Start Windows.
2. Pada penggunaan pertama, pilih **Daftar** untuk membuat akun pemilik pertama.
3. Isi nama pemilik, ID login unik 4–32 karakter, kata sandi minimal 10 karakter, dan konfirmasi kata sandi. ID login harus diawali huruf atau angka; karakter berikutnya boleh berupa huruf, angka, titik, garis bawah, atau tanda hubung.
4. Simpan kode pemulihan satu kali di tempat aman yang terpisah dari komputer. Kode ini tidak dapat ditampilkan ulang setelah pendaftaran.
5. Setelah akun pemilik dibuat, login berikutnya dilakukan melalui pilihan **Login sebagai Pemilik** atau **Login sebagai Pegawai**.

Akun pemilik pertama hanya dapat didaftarkan saat belum ada akun pemilik pada database lokal. Pemilik dapat mengelola akun pegawai dari menu yang tersedia setelah login. Jalur login pemilik dan pegawai terpisah.\n\nJika Anda memperbarui dari build lama yang meminta NIK 16 digit, masukkan angka yang sama pada kolom **ID login** saat pertama kali masuk setelah pembaruan. Migrasi mempertahankan kredensial lokal yang ada; akun lama tidak otomatis diganti namanya.

**Privasi:** KasirKita tidak meminta NIK atau nomor identitas kependudukan. ID login hanya digunakan untuk mengenali akun lokal dan disimpan sebagai hash bersalt. Jangan menggunakan komputer bersama yang tidak tepercaya untuk menyimpan data usaha. Jangan membagikan ID login, kata sandi, atau kode pemulihan kepada pihak lain.

## 2. Menyiapkan katalog produk

1. Buka tab **Produk**.
2. Pilih **Tambah produk**.
3. Masukkan SKU unik, nama produk, harga dalam rupiah, dan stok awal.
4. Gunakan SKU otomatis bila diperlukan. SKU seperti `KK-000001` adalah kode internal KasirKita, bukan nomor GTIN resmi.
5. Periksa harga dan stok sebelum memulai transaksi.

Produk yang sudah terpakai di transaksi lama sebaiknya dinonaktifkan daripada dihapus agar riwayat transaksi tetap dapat ditelusuri. Penyesuaian stok dilakukan melalui tindakan stok yang tersedia agar perubahan tercatat.

## 3. Mencatat transaksi tunai

1. Buka tab **Kasir**.
2. Cari produk, pilih jumlah, lalu tambahkan ke keranjang.
3. Periksa item, kuantitas, diskon, dan total.
4. Masukkan jumlah uang tunai yang diterima.
5. Pilih **Proses pembayaran** dan periksa konfirmasi transaksi.
6. Simpan struk TXT atau PDF dari detail transaksi jika diperlukan.

KasirKita memvalidasi harga, status produk, stok, dan pembayaran sebelum transaksi disimpan. Metode pembayaran yang didukung pada versi ini adalah tunai. QRIS, transfer bank, pembayaran kartu, utang/piutang, dan sinkronisasi cloud belum termasuk dalam versi ini.

## 4. Memeriksa riwayat dan laporan

- Buka **Riwayat transaksi** untuk memilih transaksi dan melihat rinciannya.
- Buka **Laporan** untuk menentukan rentang tanggal dan melihat ringkasan.
- Ekspor laporan yang diperlukan ke CSV, Excel `.xlsx`, atau PDF sesuai opsi yang tersedia.
- Periksa kembali angka transaksi dan laporan sebelum digunakan untuk keputusan bisnis.

Laporan KasirKita membantu pencatatan operasional; laporan ini bukan pengganti pembukuan formal atau nasihat akuntansi/pajak.

## 5. Data pelanggan, supplier, dan operasional

Pada versi yang menyediakan tab tersebut, pemilik dapat mengelola data pelanggan dan supplier, harga modal, penyesuaian stok, pengeluaran, retur, serta ringkasan laba. Periksa setiap catatan sebelum menyimpannya. Retur hanya dilakukan terhadap transaksi yang benar dan jumlah yang belum diretur.

## 6. Mengatur pajak

Pajak nonaktif secara default. Bila usaha memerlukan perhitungan pajak, verifikasi label, tarif, dan cara menghitung terlebih dahulu sesuai keadaan usaha dan peraturan yang berlaku. KasirKita adalah alat hitung yang dapat dikonfigurasi, bukan sertifikasi kepatuhan pajak; tarif tidak diperbarui otomatis.

Perubahan pengaturan berlaku untuk transaksi berikutnya dan tidak semestinya mengubah snapshot transaksi lama. Tetap periksa hasil kalkulasi dengan contoh yang dihitung secara terpisah sebelum dipakai untuk transaksi sungguhan.

## 7. Membuat backup dan memulihkan data

1. Buka menu **Riwayat transaksi** atau kontrol backup yang tersedia.
2. Pilih **Buat backup** dan simpan file di lokasi aman.
3. Simpan salinan kedua pada media berbeda yang tidak selalu terhubung ke komputer.
4. Untuk pemulihan, pilih file backup, baca peringatan, lalu konfirmasi hanya setelah yakin.
5. Setelah pemulihan selesai, periksa kembali katalog, transaksi, stok, dan pengaturan.

Pemulihan mengganti database aktif. Jangan mengganti, memindahkan, atau menghapus file database saat aplikasi sedang berjalan. KasirKita tidak menyinkronkan data ke cloud; kehilangan perangkat atau file lokal dapat menyebabkan kehilangan data jika tidak tersedia backup.

## 8. Lokasi data dan log

Pada Windows, database dan log biasanya berada di:

`%LOCALAPPDATA%\\KasirKita`

Folder tersebut terpisah dari folder program. Jangan hapus folder ini saat memperbarui aplikasi atau menghapus shortcut. Sebelum menghapus data atau melepas aplikasi, buat dan verifikasi backup terlebih dahulu.

Informasi perangkat pada tab **Perangkat** digunakan untuk menampilkan versi Windows, arsitektur, memori, prosesor, resolusi, dan profil penggunaan sumber daya. Deteksi tersebut tidak menjamin bahwa semua versi Windows telah teruji.

## 9. Batasan penting

- Target kompatibilitas yang direncanakan adalah Windows 10 dan Windows 11; pemasangan pada Windows 8.1 belum diverifikasi secara fisik.
- Aplikasi beroperasi menggunakan database lokal. Tidak tersedia sinkronisasi lintas perangkat atau cloud.
- Scanner USB hanya didukung bila perangkat bertindak seperti keyboard dan mengirim SKU diikuti Enter.
- Label Code 128 dibuat dari SKU internal, bukan kode produk resmi GS1/GTIN.
- Pajak hanya dapat dikonfigurasi secara manual dan tidak memastikan kepatuhan hukum.
- Buat backup berkala dan periksa angka transaksi, stok, serta laporan secara mandiri.

## 10. Bantuan

Untuk bantuan produk, kunjungi [Choco AI](https://choco-ai-platform.netlify.app/) atau hubungi The Choco Studios melalui `thechocostudio@gmail.com`. Saat melaporkan masalah, jelaskan versi aplikasi, versi Windows, langkah yang dilakukan, dan pesan kesalahan. Jangan kirim database usaha, kata sandi, atau kode pemulihan melalui laporan dukungan biasa.
