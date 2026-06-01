# 📸 Sistem Absensi Face Recognition

Sistem absensi otomatis berbasis web menggunakan pengenalan wajah dengan Python, Flask, OpenCV, dan MySQL.

## ✨ Fitur Utama

### 🔐 Sistem Login & Role Management
- Login dengan username & password (bcrypt encryption)
- 2 Role: **Admin** dan **User (Siswa)**
- Dashboard terpisah untuk Admin dan User
- Session management yang aman

### 👨‍💼 Dashboard Admin
- Kelola siswa/karyawan (CRUD lengkap)
- Kelola user akun (CRUD lengkap)
- Registrasi siswa baru dengan face recognition
- Training model face recognition
- Jalankan absensi real-time
- Laporan absensi (harian, rentang tanggal, per siswa, per kelas)
- Statistik kehadiran lengkap
- Export laporan ke CSV

### 👤 Dashboard User (Siswa)
- Lihat profil pribadi
- Lihat riwayat absensi dengan filter
- Lihat statistik kehadiran pribadi
- Ganti password

### 🎯 Fitur Absensi
- Face recognition real-time via server webcam
- Pencegahan absensi ganda per hari
- Status kehadiran (Hadir/Terlambat)
- Confidence score tracking
- Auto-detect dan record
- Video streaming dari server camera

## 🛠️ Teknologi

- **Backend**: Python 3.8+, Flask
- **Database**: MySQL 5.7+
- **Face Recognition**: OpenCV, LBPH Algorithm
- **Authentication**: bcrypt
- **Frontend**: HTML5, CSS3, JavaScript

## 📋 Persyaratan Sistem

- Python 3.8 atau lebih tinggi
- MySQL Server 5.7 atau lebih tinggi
- Webcam
- Windows/Linux/macOS

## 🚀 Instalasi

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database
Jalankan file SQL di MySQL:
```bash
mysql -u root -p < database/complete_database_setup.sql
```

Atau via MySQL client:
```sql
SOURCE database/complete_database_setup.sql;
```

### 3. Konfigurasi Environment
Copy file `.env.example` menjadi `.env` dan sesuaikan:
```bash
cp .env.example .env
```

Edit `.env`:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=attendance_db
LATE_AFTER=08:00:00
CONFIDENCE_THRESHOLD=50
```

### 4. Generate SSL Certificate (untuk HTTPS)
```bash
python -c "from OpenSSL import crypto; k = crypto.PKey(); k.generate_key(crypto.TYPE_RSA, 2048); cert = crypto.X509(); cert.get_subject().CN = '192.168.1.22'; cert.set_serial_number(1000); cert.gmtime_adj_notBefore(0); cert.gmtime_adj_notAfter(365*24*60*60); cert.set_issuer(cert.get_subject()); cert.set_pubkey(k); cert.sign(k, 'sha256'); open('cert.pem', 'wb').write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert)); open('key.pem', 'wb').write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))"
```

### 5. Jalankan Website
```bash
python app.py
```

### 6. Akses Website
Buka browser: `https://192.168.1.22:5000` atau `https://127.0.0.1:5000`

**Catatan:** Klik "Advanced" → "Proceed to 192.168.1.22 (unsafe)" jika muncul warning SSL

## 🔑 Login Pertama Kali

**Akun Admin Default:**
- Username: `admin`
- Password: `admin123`

⚠️ **PENTING:** Segera ganti password setelah login pertama!

## 📖 Cara Penggunaan

### Untuk Siswa Baru (Registrasi Mandiri)

#### 1. Registrasi Akun
1. Buka browser: `https://192.168.1.22:5000`
2. Klik **"Daftar Sekarang"** di halaman login
3. Isi form registrasi:
   - NIS/NIM
   - Nama Lengkap
   - Kelas/Jurusan
   - Jenis Kelamin
   - Password (minimal 6 karakter)
4. Klik **"Daftar"**
5. Akun siswa dan user otomatis terbuat

#### 2. Login
- Username: **NIS Anda** (contoh: `12345`)
- Password: **Password yang Anda buat saat registrasi**

#### 3. Registrasi Wajah
1. Setelah login, klik **"Registrasi Wajah"** di sidebar
2. Klik **"Mulai Kamera"** (kamera server akan aktif)
3. Posisikan wajah Anda di depan kamera
4. Klik **"Ambil Foto (30x)"**
5. Sistem akan mengambil 30 foto otomatis dari kamera server
6. Tunggu hingga selesai

#### 4. Training Model (Perlu dilakukan Admin/Manual)
Setelah registrasi wajah, jalankan training model via PowerShell:
```bash
cd "C:\Users\Gaby\Documents\File Ester\Sistem Absensi"
.\.venv\Scripts\python.exe -m src.train_model
```

#### 5. Absensi
1. Klik **"Absensi Sekarang"** di sidebar
2. Klik **"Mulai Kamera"**
3. Posisikan wajah Anda di depan kamera
4. Klik **"Absen Sekarang"**
5. Sistem akan mengenali wajah dan mencatat absensi

#### 6. Lihat Riwayat Absensi
1. Dashboard menampilkan ringkasan kehadiran
2. Klik **"Riwayat Absensi"** untuk detail
3. Filter berdasarkan periode

#### 7. Lihat Statistik
1. Klik **"Statistik Saya"**
2. Lihat total kehadiran, tepat waktu, terlambat
3. Lihat statistik per bulan

### Untuk Admin

#### 1. Login
- Username: `admin`
- Password: `admin123` (ganti setelah login pertama)

#### 2. Kelola Siswa
1. Klik **"Kelola Siswa"**
2. Lihat daftar semua siswa
3. Edit/Hapus siswa jika diperlukan

#### 3. Kelola User
1. Klik **"Kelola User"**
2. Tambah/Edit/Hapus user
3. Reset password user

#### 4. Training Model
Jalankan via PowerShell setiap ada siswa baru yang registrasi wajah:
```bash
cd "C:\Users\Gaby\Documents\File Ester\Sistem Absensi"
.\.venv\Scripts\python.exe -m src.train_model
```

#### 5. Lihat Laporan
1. Klik **"Laporan"**
2. Pilih jenis laporan (harian, rentang tanggal, per siswa, per kelas)
3. Filter sesuai kebutuhan
4. Export ke CSV jika diperlukan

#### 6. Lihat Statistik
1. Klik **"Statistik"**
2. Lihat statistik kehadiran keseluruhan
3. Analisis data absensi

## 📁 Struktur Folder

```
Sistem Absensi/
├── app.py                      # Main Flask application
├── routes_admin.py             # Admin routes (kelola siswa)
├── routes_admin_users.py       # Admin routes (kelola user & laporan)
├── routes_user.py              # User routes (dashboard siswa)
├── requirements.txt            # Python dependencies
├── .env                        # Konfigurasi (buat dari .env.example)
├── .env.example                # Template konfigurasi
├── README.md                   # Dokumentasi ini
├── PANDUAN_DASHBOARD.md        # Panduan lengkap dashboard
│
├── database/                   # Database setup files
│   ├── complete_database_setup.sql  # Setup lengkap (1 file)
│   ├── fix_admin_password.sql       # Fix password admin
│   └── README.md                    # Dokumentasi database
│
├── src/                        # Source code modules
│   ├── __init__.py
│   ├── database.py             # Database connection
│   ├── auth_web.py             # Web authentication
│   ├── register_student.py     # Student registration
│   ├── train_model.py          # Model training
│   ├── attendance.py           # Attendance system
│   └── export_report.py        # Export reports
│
├── templates/                  # HTML templates
│   ├── login.html              # Login page
│   ├── admin/                  # Admin templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── students.html
│   │   ├── users.html
│   │   └── ...
│   └── user/                   # User templates
│       ├── base.html
│       ├── dashboard.html
│       ├── profile.html
│       └── ...
│
├── static/                     # Static files (CSS, JS, images)
├── model/                      # Trained models (auto-generated)
├── dataset/                    # Face samples (auto-generated)
└── exports/                    # Exported reports (auto-generated)
```

## 🔧 Troubleshooting

### Login Gagal
- Pastikan database sudah di-setup
- Cek username dan password
- Pastikan akun aktif (is_active = 1)

### Kamera Tidak Terdeteksi
- Pastikan webcam terhubung ke server
- Kamera server-side (bukan browser webcam)
- Cek izin akses kamera di sistem operasi
- Restart Flask app jika kamera tidak muncul

### Wajah Tidak Dikenali
- Pastikan model sudah di-training
- Pastikan pencahayaan cukup
- Tambah sampel wajah dengan registrasi ulang
- Sesuaikan CONFIDENCE_THRESHOLD di .env (default: 70)

### Database Error
- Pastikan MySQL server berjalan
- Cek konfigurasi di .env
- Pastikan user memiliki privilege

### Port 5000 Sudah Digunakan
Edit `app.py` baris terakhir:
```python
app.run(debug=True, host='0.0.0.0', port=5001, ssl_context=('cert.pem', 'key.pem'))
```

### SSL Certificate Error
- Klik "Advanced" → "Proceed to 192.168.1.22 (unsafe)" di browser
- Self-signed certificate normal untuk development
- Generate ulang certificate jika expired

## 📚 Dokumentasi Lengkap

- **PANDUAN_DASHBOARD.md** - Panduan lengkap penggunaan dashboard
- **database/README.md** - Dokumentasi database setup

## 🔒 Keamanan

- Password di-hash dengan bcrypt
- Session management dengan Flask
- Role-based access control
- SQL injection protection
- XSS protection

## 📝 Lisensi

Proyek ini dibuat untuk keperluan akademik dan pembelajaran.

## 👨‍💻 Kontributor

Dikembangkan sebagai sistem absensi berbasis face recognition dengan web interface.

---

**© 2026 Sistem Absensi Face Recognition**
