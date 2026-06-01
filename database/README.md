# Database Setup Files

Folder ini berisi file SQL untuk setup database sistem absensi.

## File yang Tersedia

### 1. database_setup.sql
File ini berisi:
- Struktur tabel utama (students, face_samples, attendance)
- Views untuk reporting
- Stored procedures
- Sample data (optional)

**Cara menggunakan:**
```sql
mysql -u root -p < database/database_setup.sql
```

Atau buka MySQL client dan jalankan:
```sql
SOURCE database/database_setup.sql;
```

### 2. database_users_setup.sql
File ini berisi:
- Tabel users untuk autentikasi
- Akun admin default

**Akun Admin Default:**
- Username: `admin`
- Password: `admin123`

⚠️ **PENTING:** Ganti password admin setelah login pertama kali!

**Cara menggunakan:**
```sql
mysql -u root -p < database/database_users_setup.sql
```

Atau buka MySQL client dan jalankan:
```sql
SOURCE database/database_users_setup.sql;
```

## Urutan Setup

1. **Setup database utama:**
   ```bash
   mysql -u root -p < database/database_setup.sql
   ```

2. **Setup tabel users:**
   ```bash
   mysql -u root -p < database/database_users_setup.sql
   ```

3. **Verifikasi:**
   ```sql
   USE attendance_db;
   SHOW TABLES;
   ```

   Anda harus melihat tabel:
   - students
   - face_samples
   - attendance
   - users

## Konfigurasi Database

Edit file `.env` untuk konfigurasi koneksi database:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=attendance_db
```

## Troubleshooting

### Error: Access denied
- Pastikan username dan password MySQL benar
- Pastikan user memiliki privilege untuk CREATE DATABASE

### Error: Table already exists
- Database sudah pernah di-setup sebelumnya
- Aman untuk diabaikan jika menggunakan `IF NOT EXISTS`

### Error: Cannot connect to MySQL server
- Pastikan MySQL service berjalan
- Cek host dan port di file `.env`

## Backup Database

Untuk backup database:
```bash
mysqldump -u root -p attendance_db > backup_$(date +%Y%m%d).sql
```

## Restore Database

Untuk restore dari backup:
```bash
mysql -u root -p attendance_db < backup_20260531.sql
```
