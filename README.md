# KasirKita Desktop

KasirKita adalah aplikasi kasir desktop lokal untuk usaha mikro dan kecil. Repositori ini berisi aplikasi Python/Tkinter dengan database SQLite, layanan transaksi dan stok, pengelolaan akun, laporan, serta utilitas backup dan restore.

**Status rilis: BELUM SIAP UNTUK DIJUAL.** Status ini mengikuti [Release Gate Checklist](docs/RELEASE_CHECKLIST.md). Keberadaan kode sumber atau file installer lama di repositori tidak berarti rilis telah disetujui.

## Implementasi utama

- Aplikasi desktop dengan antarmuka Tkinter/ttk.
- Penyimpanan SQLite lokal tanpa kewajiban akun cloud atau koneksi internet.
- Katalog produk, pencarian, dan pengelolaan stok.
- Alur checkout, riwayat transaksi, dan laporan penjualan.
- Pengaturan pajak generik yang nonaktif secara default.
- Akun Owner dan karyawan serta pengelolaan kontak.
- Backup dan restore database lokal.
- Ekspor laporan dan dokumen melalui dependensi yang tercantum pada `requirements-build.txt`.

Daftar di atas menjelaskan komponen yang ditemukan dalam implementasi. Kelengkapan alur, kompatibilitas Windows, kualitas paket installer, dan kesiapan penggunaan nyata tetap harus mengikuti bukti pengujian pada checklist rilis.

## Teknologi dan data

- Python.
- Tkinter/ttk untuk antarmuka desktop.
- SQLite untuk penyimpanan lokal.
- `unittest` untuk pengujian otomatis.
- PyInstaller dan Inno Setup untuk alur packaging Windows.

Data aplikasi disimpan pada direktori per pengguna:
- Windows: `%LOCALAPPDATA%\KasirKita`
- macOS: `~/Library/Application Support/KasirKita`
- Linux: `~/.local/share/KasirKita`

Database dan log tidak disimpan di samping executable secara default.

## Menjalankan aplikasi dari source

Gunakan Python yang sesuai dengan matriks versi pada workflow. Dari root repositori:

```bash
python -m kasirkita
```

## Pemeriksaan otomatis

Workflow CI saat ini menjalankan pemeriksaan pada Ubuntu dan Windows dengan Python 3.8 serta 3.12:

```bash
python -m pip install -r requirements-build.txt
python -m compileall -q kasirkita tests
python -m unittest discover -v
```

Dependensi build dan ekspor lokal dicatat pada [requirements-build.txt](requirements-build.txt).

## Dokumentasi proyek

- [Arsitektur Desktop v1](docs/ARCHITECTURE_DESKTOP_V1.md)
- [Persyaratan Desktop v1](docs/REQUIREMENTS_DESKTOP_V1.md)
- [Panduan pengguna alpha](docs/PANDUAN_PENGGUNA_ALPHA.md)
- [Release Gate Checklist](docs/RELEASE_CHECKLIST.md)
- [Alur autentikasi dan pengelolaan akun](docs/AUTHENTICATION_AND_ACCOUNT_MANAGEMENT.md)

## Dokumen kebijakan TCS

Repositori ini juga masih memuat dokumen Ketentuan Layanan, Kebijakan Privasi, dan Kebijakan Penggunaan TCS dalam Bahasa Indonesia dan Inggris. Dokumen tersebut merupakan kebijakan umum TCS, bukan panduan penggunaan KasirKita. File dipertahankan agar tidak menghapus materi legal yang sudah ada; pemisahan ke repositori dokumentasi tersendiri memerlukan penataan repositori terpisah.

## Gerbang rilis

Jangan mendistribusikan aplikasi sebagai rilis siap pakai atau menjualnya sebelum semua butir wajib pada [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) memiliki bukti dan persetujuan. Pengujian pada satu sistem operasi tidak membuktikan kompatibilitas pada seluruh versi Windows.
