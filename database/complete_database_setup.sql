-- ============================================================
-- SISTEM ABSENSI FACE RECOGNITION - COMPLETE DATABASE SETUP
-- ============================================================
-- File: complete_database_setup.sql
-- Description: Complete database setup including tables and default admin
-- Date: 2026-05-31
-- ============================================================

-- Create database
CREATE DATABASE IF NOT EXISTS attendance_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- Use the database
USE attendance_db;

-- ============================================================
-- TABLE: students
-- Description: Stores student/employee information
-- ============================================================
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nis VARCHAR(30) UNIQUE NOT NULL COMMENT 'Nomor Induk Siswa/Karyawan',
    name VARCHAR(100) NOT NULL COMMENT 'Nama lengkap',
    class_name VARCHAR(50) DEFAULT NULL COMMENT 'Kelas atau divisi',
    gender ENUM('L', 'P') NOT NULL COMMENT 'Jenis kelamin: L=Laki-laki, P=Perempuan',
    is_active TINYINT(1) DEFAULT 1 COMMENT 'Status aktif: 1=aktif, 0=nonaktif',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu data dibuat',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Waktu data diperbarui',
    INDEX idx_nis (nis),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabel data siswa/karyawan';

-- ============================================================
-- TABLE: face_samples
-- Description: Stores face sample image paths
-- ============================================================
CREATE TABLE IF NOT EXISTS face_samples (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL COMMENT 'ID siswa (foreign key)',
    image_path VARCHAR(255) NOT NULL COMMENT 'Path file gambar wajah',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu sampel dibuat',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    INDEX idx_student_id (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabel sampel wajah siswa';

-- ============================================================
-- TABLE: attendance
-- Description: Stores attendance records
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL COMMENT 'ID siswa (foreign key)',
    attendance_date DATE NOT NULL COMMENT 'Tanggal absensi',
    check_in_time TIME NOT NULL COMMENT 'Jam masuk',
    status ENUM('Hadir', 'Terlambat') NOT NULL COMMENT 'Status kehadiran',
    confidence DECIMAL(8,2) DEFAULT NULL COMMENT 'Nilai confidence dari face recognition',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu record dibuat',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE KEY unique_attendance (student_id, attendance_date) COMMENT 'Mencegah absensi ganda per hari',
    INDEX idx_attendance_date (attendance_date),
    INDEX idx_student_date (student_id, attendance_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabel data absensi';

-- ============================================================
-- TABLE: users
-- Description: Stores user accounts for system access
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT 'Username untuk login',
    password VARCHAR(255) NOT NULL COMMENT 'Password (hashed)',
    full_name VARCHAR(100) NOT NULL COMMENT 'Nama lengkap user',
    role ENUM('admin', 'user') NOT NULL DEFAULT 'user' COMMENT 'Role: admin atau user',
    student_id INT DEFAULT NULL COMMENT 'Link ke students table (untuk role user)',
    is_active TINYINT(1) DEFAULT 1 COMMENT 'Status aktif: 1=aktif, 0=nonaktif',
    last_login TIMESTAMP NULL DEFAULT NULL COMMENT 'Waktu login terakhir',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu akun dibuat',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Waktu data diperbarui',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL,
    INDEX idx_username (username),
    INDEX idx_role (role),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabel user untuk autentikasi sistem';

-- ============================================================
-- VIEWS (Optional - Useful for reporting)
-- ============================================================

-- View: Daily attendance summary
CREATE OR REPLACE VIEW v_daily_attendance AS
SELECT
    a.attendance_date,
    COUNT(DISTINCT a.student_id) as total_hadir,
    SUM(CASE WHEN a.status = 'Hadir' THEN 1 ELSE 0 END) as tepat_waktu,
    SUM(CASE WHEN a.status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat
FROM attendance a
GROUP BY a.attendance_date
ORDER BY a.attendance_date DESC;

-- View: Student attendance detail
CREATE OR REPLACE VIEW v_student_attendance AS
SELECT
    s.nis,
    s.name,
    s.class_name,
    s.gender,
    a.attendance_date,
    a.check_in_time,
    a.status,
    a.confidence
FROM students s
LEFT JOIN attendance a ON s.id = a.student_id
WHERE s.is_active = 1
ORDER BY a.attendance_date DESC, a.check_in_time ASC;

-- View: Student attendance statistics
CREATE OR REPLACE VIEW v_student_stats AS
SELECT
    s.id,
    s.nis,
    s.name,
    s.class_name,
    COUNT(a.id) as total_kehadiran,
    SUM(CASE WHEN a.status = 'Hadir' THEN 1 ELSE 0 END) as hadir_tepat_waktu,
    SUM(CASE WHEN a.status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat,
    ROUND(AVG(a.confidence), 2) as avg_confidence
FROM students s
LEFT JOIN attendance a ON s.id = a.student_id
WHERE s.is_active = 1
GROUP BY s.id, s.nis, s.name, s.class_name
ORDER BY s.name;

-- ============================================================
-- STORED PROCEDURES (Optional - Advanced features)
-- ============================================================

-- Procedure: Get attendance by date range
DELIMITER //
CREATE PROCEDURE sp_get_attendance_by_date(
    IN start_date DATE,
    IN end_date DATE
)
BEGIN
    SELECT
        s.nis,
        s.name,
        s.class_name,
        a.attendance_date,
        a.check_in_time,
        a.status,
        a.confidence
    FROM attendance a
    INNER JOIN students s ON a.student_id = s.id
    WHERE a.attendance_date BETWEEN start_date AND end_date
    ORDER BY a.attendance_date DESC, a.check_in_time ASC;
END //
DELIMITER ;

-- Procedure: Get student attendance summary
DELIMITER //
CREATE PROCEDURE sp_student_summary(
    IN student_nis VARCHAR(30)
)
BEGIN
    SELECT
        s.nis,
        s.name,
        s.class_name,
        COUNT(a.id) as total_kehadiran,
        SUM(CASE WHEN a.status = 'Hadir' THEN 1 ELSE 0 END) as hadir,
        SUM(CASE WHEN a.status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat,
        MIN(a.attendance_date) as first_attendance,
        MAX(a.attendance_date) as last_attendance
    FROM students s
    LEFT JOIN attendance a ON s.id = a.student_id
    WHERE s.nis = student_nis
    GROUP BY s.id, s.nis, s.name, s.class_name;
END //
DELIMITER ;

-- ============================================================
-- DEFAULT ADMIN ACCOUNT
-- ============================================================
-- Password: admin123 (hashed dengan bcrypt)
-- IMPORTANT: Ganti password ini setelah login pertama kali!
INSERT INTO users (username, password, full_name, role, is_active) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/qvIyW', 'Administrator', 'admin', 1)
ON DUPLICATE KEY UPDATE username=username;

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- Check if tables are created
SELECT 'Tables created successfully!' as Status;

SELECT
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'attendance_db'
ORDER BY TABLE_NAME;

-- ============================================================
-- SETUP COMPLETE
-- ============================================================
-- Database setup completed successfully!
--
-- Next steps:
-- 1. Verify tables: SHOW TABLES;
-- 2. Login ke website dengan:
--    Username: admin
--    Password: admin123
-- 3. SEGERA ganti password admin setelah login!
--
-- Optional queries:
-- - SELECT * FROM v_daily_attendance;
-- - SELECT * FROM v_student_stats;
-- - CALL sp_get_attendance_by_date('2026-01-01', '2026-12-31');
-- ============================================================
