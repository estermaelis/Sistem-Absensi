# Product Requirements Document (PRD)

# Sistem Absensi Karyawan Berbasis Face Recognition Menggunakan OpenCV dan Python

## 1. Informasi Produk

### Nama Produk

FaceAttend

### Nama Perusahaan

PT Nexa Teknologi Indonesia

### Jenis Perusahaan

Startup Teknologi

### Versi Dokumen

1.0

### Tanggal

Juni 2026

### Penyusun

Tim Pengembang Sistem Informasi

---

# 2. Latar Belakang

PT Nexa Teknologi Indonesia merupakan perusahaan startup yang bergerak di bidang pengembangan perangkat lunak dan solusi digital. Saat ini proses absensi karyawan masih dilakukan secara manual sehingga berpotensi menimbulkan kesalahan pencatatan, keterlambatan rekapitulasi data, serta risiko kecurangan seperti titip absen.

Untuk mengatasi permasalahan tersebut diperlukan sistem absensi berbasis web yang memanfaatkan teknologi Face Recognition sehingga proses kehadiran dapat dilakukan secara otomatis, akurat, dan real-time.

---

# 3. Tujuan Produk

* Mengotomatisasi proses absensi karyawan.
* Mengurangi praktik titip absen.
* Mempercepat proses pencatatan kehadiran.
* Mempermudah HR dalam melakukan monitoring absensi.
* Menyediakan laporan absensi secara real-time.
* Meningkatkan keamanan dan validitas data kehadiran.

---

# 4. Ruang Lingkup Sistem

Sistem mencakup:

* Manajemen data karyawan
* Registrasi wajah karyawan
* Training dataset wajah
* Proses absensi masuk dan pulang
* Monitoring kehadiran
* Pembuatan laporan absensi
* Manajemen akun pengguna

---

# 5. Profil Perusahaan

## PT Nexa Teknologi Indonesia

PT Nexa Teknologi Indonesia merupakan perusahaan startup yang bergerak dalam bidang:

* Software Development
* Web Development
* Mobile Application Development
* Artificial Intelligence
* IT Consulting

Jumlah Karyawan: 30 Orang

---

# 6. Struktur Departemen

| ID | Nama Departemen        |
| -- | ---------------------- |
| 1  | Human Resources        |
| 2  | Information Technology |
| 3  | Product Development    |
| 4  | Marketing              |
| 5  | Finance & Accounting   |
| 6  | Customer Support       |

---

# 7. Struktur Pengguna Sistem

## 7.1 Admin

Admin memiliki akses penuh terhadap sistem.

### Hak Akses Admin

* Login
* Dashboard
* Kelola Data Karyawan
* Kelola Departemen
* Registrasi Wajah
* Training Dataset
* Monitoring Absensi
* Kelola Akun Pengguna
* Export Laporan
* Pengaturan Sistem

---

## 7.2 Karyawan

Karyawan hanya dapat mengakses data miliknya sendiri.

### Hak Akses Karyawan

* Login
* Dashboard
* Absensi Masuk
* Absensi Pulang
* Riwayat Absensi
* Profil Akun
* Ubah Password

---

# 8. Fitur Utama

## F01 - Login Sistem

Deskripsi:
Pengguna dapat masuk ke dalam sistem menggunakan akun yang telah terdaftar.

Prioritas:
High

---

## F02 - Manajemen Data Karyawan

Deskripsi:
Admin dapat menambah, mengubah, menghapus, dan melihat data karyawan.

Prioritas:
High

---

## F03 - Registrasi Wajah

Deskripsi:
Admin melakukan pengambilan dataset wajah menggunakan kamera.

Prioritas:
High

---

## F04 - Training Dataset

Deskripsi:
Sistem melakukan pelatihan model pengenalan wajah berdasarkan dataset yang telah dikumpulkan.

Prioritas:
High

---

## F05 - Absensi Masuk

Deskripsi:
Karyawan melakukan absensi masuk menggunakan kamera dan teknologi Face Recognition.

Prioritas:
High

---

## F06 - Absensi Pulang

Deskripsi:
Karyawan melakukan absensi pulang menggunakan kamera.

Prioritas:
High

---

## F07 - Monitoring Kehadiran

Deskripsi:
Admin dapat melihat daftar kehadiran seluruh karyawan secara real-time.

Prioritas:
Medium

---

## F08 - Laporan Absensi

Deskripsi:
Sistem menghasilkan laporan absensi berdasarkan periode tertentu.

Prioritas:
Medium

---

## F09 - Dashboard Statistik

Deskripsi:
Menampilkan statistik kehadiran karyawan.

Prioritas:
Medium

---

# 9. Kebutuhan Non-Fungsional

## Performa

* Waktu identifikasi wajah maksimal 3 detik.
* Sistem mampu menangani minimal 50 pengguna.

## Keamanan

* Password terenkripsi menggunakan hashing.
* Role Based Access Control (RBAC).
* Session Login.

## Ketersediaan

* Sistem dapat diakses melalui browser.
* Sistem berjalan pada jaringan lokal perusahaan.

---

# 10. Teknologi yang Digunakan

## Backend

* Python 3.x
* Flask

## Face Recognition

* OpenCV
* face_recognition
* NumPy

## Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript

## Database

* MySQL

---

# 11. Alur Registrasi Wajah

1. Admin login.
2. Admin menambahkan data karyawan.
3. Admin membuka menu registrasi wajah.
4. Kamera aktif.
5. Sistem mengambil 50–100 citra wajah.
6. Dataset disimpan.
7. Sistem melakukan training model.
8. Model siap digunakan.

---

# 12. Alur Absensi

1. Karyawan login.
2. Membuka halaman absensi.
3. Kamera aktif.
4. Sistem mendeteksi wajah.
5. Sistem mencocokkan wajah dengan dataset.
6. Sistem memverifikasi identitas.
7. Data kehadiran disimpan ke database.
8. Sistem menampilkan notifikasi berhasil.

---

# 13. Struktur Database

## users

* id
* username
* password
* role

## departments

* id
* department_name

## employees

* id
* employee_number
* full_name
* email
* department_id

## face_dataset

* id
* employee_id
* image_path

## attendance

* id
* employee_id
* attendance_date
* check_in
* check_out
* status

---

# 14. Dashboard Admin

Dashboard menampilkan:

* Total Karyawan
* Total Departemen
* Hadir Hari Ini
* Terlambat
* Tidak Hadir
* Grafik Kehadiran Bulanan
* Aktivitas Terbaru

---

# 15. Dashboard Karyawan

Dashboard menampilkan:

* Data Profil
* Status Kehadiran Hari Ini
* Jam Masuk
* Jam Pulang
* Riwayat Absensi
* Persentase Kehadiran

---

# 16. Kriteria Keberhasilan

Sistem dianggap berhasil apabila:

* Wajah karyawan dapat dikenali dengan akurasi tinggi.
* Data absensi tersimpan secara otomatis.
* Admin dapat mengelola seluruh data melalui dashboard.
* Laporan absensi dapat dihasilkan secara otomatis.
* Sistem dapat digunakan oleh seluruh karyawan perusahaan.

---

# 17. Kesimpulan

FaceAttend merupakan sistem absensi karyawan berbasis web yang memanfaatkan teknologi Face Recognition menggunakan OpenCV dan Python. Sistem ini dirancang untuk membantu PT Nexa Teknologi Indonesia dalam meningkatkan efisiensi pencatatan kehadiran, mengurangi kecurangan absensi, serta menyediakan laporan kehadiran yang akurat dan real-time.
