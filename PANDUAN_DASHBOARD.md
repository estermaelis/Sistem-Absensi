# PANDUAN SISTEM DASHBOARD ABSENSI

## Deskripsi
Sistem Absensi Face Recognition dengan dashboard terpisah untuk Admin dan User.

## Fitur Utama

### Dashboard Admin
- Kelola data siswa/karyawan (tambah, edit, hapus, aktifkan/nonaktifkan)
- Kelola user akun (tambah, edit, reset password, hapus)
- Registrasi siswa baru dengan face recognition
- Training model face recognition
- Jalankan sistem absensi
- Lihat laporan absensi (harian, rentang tanggal, per siswa, per kelas)
- Export laporan ke CSV
- Statistik kehadiran lengkap
- Ganti password admin

### Dashboard User
- Lihat profil pribadi
- Lihat riwayat absensi pribadi
- Lihat statistik kehadiran pribadi
- Lihat absensi bulan ini
- Ganti password

## Instalasi

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database
Jalankan aplikasi dan pilih menu:
- Menu 2: Inisialisasi Database (membuat database dan tabel utama)
- Menu 3: Setup Tabel User (membuat tabel user dan akun admin default)

### 3. Akun Admin Default
Setelah setup tabel user, gunakan akun berikut untuk login pertama kali:
- **Username**: admin
- **Password**: admin123

⚠️ **PENTING**: Segera ganti password admin setelah login pertama kali!

## Cara Menggunakan

### Login
1. Jalankan aplikasi: `python main.py`
2. Pilih menu 1 (Login)
3. Masukkan username dan password
4. Sistem akan otomatis mengarahkan ke dashboard sesuai role (Admin/User)

### Untuk Admin

#### Kelola Siswa/Karyawan
1. Dari dashboard admin, pilih menu 1
2. Pilih operasi yang diinginkan:
   - Lihat semua siswa
   - Cari siswa (berdasarkan NIS atau nama)
   - Edit data siswa
   - Ubah status aktif/nonaktif
   - Hapus siswa (akan menghapus semua data terkait)

#### Kelola User Akun
1. Dari dashboard admin, pilih menu 2
2. Pilih operasi yang diinginkan:
   - Lihat semua user
   - Tambah user baru (admin atau user biasa)
   - Edit data user
   - Reset password user
   - Ubah status aktif/nonaktif
   - Hapus user

#### Registrasi Siswa Baru
1. Dari dashboard admin, pilih menu 3
2. Ikuti proses registrasi:
   - Masukkan data siswa (NIS, nama, kelas, gender)
   - Ambil foto wajah (30 sampel)
   - Data akan tersimpan di database

#### Training Model
1. Dari dashboard admin, pilih menu 4
2. Sistem akan melatih model dengan semua data wajah yang ada
3. Model akan disimpan untuk digunakan saat absensi

#### Jalankan Absensi
1. Dari dashboard admin, pilih menu 5
2. Kamera akan aktif untuk mendeteksi wajah
3. Sistem akan otomatis mencatat kehadiran

#### Lihat Laporan
1. Dari dashboard admin, pilih menu 6
2. Pilih jenis laporan:
   - Laporan harian (absensi per tanggal)
   - Laporan rentang tanggal
   - Laporan per siswa (riwayat absensi siswa tertentu)
   - Laporan per kelas (ringkasan per kelas)

#### Export Laporan
1. Dari dashboard admin, pilih menu 7
2. Laporan akan diekspor ke file CSV

#### Statistik Kehadiran
1. Dari dashboard admin, pilih menu 8
2. Lihat statistik keseluruhan dan bulan ini
3. Lihat top 5 siswa paling rajin

### Untuk User

#### Lihat Profil
1. Dari dashboard user, pilih menu 1
2. Lihat informasi profil pribadi (NIS, nama, kelas, dll)

#### Lihat Riwayat Absensi
1. Dari dashboard user, pilih menu 2
2. Pilih filter tanggal:
   - 7 hari terakhir
   - 30 hari terakhir
   - Semua data
   - Custom range
3. Lihat detail absensi dengan tanggal, jam, status, dan confidence

#### Lihat Statistik Kehadiran
1. Dari dashboard user, pilih menu 3
2. Lihat statistik keseluruhan:
   - Total kehadiran
   - Hadir tepat waktu vs terlambat
   - Persentase ketepatan waktu
   - Rata-rata confidence
3. Lihat statistik per bulan tahun ini

#### Lihat Absensi Bulan Ini
1. Dari dashboard user, pilih menu 4
2. Lihat semua absensi bulan berjalan

#### Ganti Password
1. Dari dashboard user, pilih menu 5
2. Masukkan password lama
3. Masukkan password baru (minimal 6 karakter)
4. Konfirmasi password baru

## Struktur Database

### Tabel: users
- id (Primary Key)
- username (Unique)
- password (Hashed dengan bcrypt)
- full_name
- role (admin/user)
- student_id (Foreign Key ke students, untuk role user)
- is_active
- last_login
- created_at
- updated_at

### Tabel: students
- id (Primary Key)
- nis (Unique)
- name
- class_name
- gender (L/P)
- is_active
- created_at
- updated_at

### Tabel: face_samples
- id (Primary Key)
- student_id (Foreign Key)
- image_path
- created_at

### Tabel: attendance
- id (Primary Key)
- student_id (Foreign Key)
- attendance_date
- check_in_time
- status (Hadir/Terlambat)
- confidence
- created_at

## Keamanan

### Password
- Password di-hash menggunakan bcrypt
- Minimal 6 karakter
- Tidak disimpan dalam bentuk plain text

### Session Management
- Session disimpan dalam memory selama aplikasi berjalan
- Logout akan menghapus session
- Setiap user hanya bisa mengakses data sesuai role-nya

### Role-Based Access Control
- **Admin**: Akses penuh ke semua fitur
- **User**: Hanya bisa melihat data pribadi

## Tips Penggunaan

1. **Untuk Admin**:
   - Selalu backup database secara berkala
   - Ganti password admin default segera setelah instalasi
   - Buat user akun untuk setiap siswa yang ingin mengakses sistem
   - Link user akun dengan data siswa agar user bisa melihat absensi mereka

2. **Untuk User**:
   - Ganti password default jika diberikan oleh admin
   - Cek absensi secara berkala untuk memastikan data akurat
   - Hubungi admin jika ada ketidaksesuaian data

3. **Umum**:
   - Pastikan kamera berfungsi dengan baik untuk absensi
   - Training model secara berkala jika ada siswa baru
   - Gunakan pencahayaan yang baik saat registrasi dan absensi

## Troubleshooting

### Login Gagal
- Pastikan username dan password benar
- Pastikan akun aktif (is_active = 1)
- Cek apakah tabel users sudah dibuat (menu 3)

### User Tidak Bisa Lihat Absensi
- Pastikan user akun sudah di-link dengan data siswa (student_id)
- Hubungi admin untuk melakukan linking

### Database Error
- Pastikan MySQL server berjalan
- Cek konfigurasi di file .env
- Pastikan database sudah diinisialisasi (menu 2)

### Model Face Recognition Error
- Pastikan sudah ada data siswa terdaftar
- Jalankan training model (menu 4 di dashboard admin)
- Pastikan folder face_samples ada dan berisi foto

## File Penting

- `main.py` - Entry point aplikasi
- `src/auth.py` - Modul autentikasi
- `src/dashboard_admin.py` - Dashboard admin
- `src/dashboard_user.py` - Dashboard user
- `src/admin_students.py` - Manajemen siswa
- `src/admin_users.py` - Manajemen user
- `src/admin_reports.py` - Laporan dan statistik
- `database_setup.sql` - Setup database utama
- `database_users_setup.sql` - Setup tabel user
- `.env` - Konfigurasi database dan sistem

## Lisensi
Sistem ini dibuat untuk keperluan pendidikan dan internal.

## Support
Untuk bantuan lebih lanjut, hubungi administrator sistem.
