-- ============================================================
-- SISTEM ABSENSI KARYAWAN FACE RECOGNITION - COMPLETE DATABASE SETUP
-- ============================================================
-- File: complete_database_setup.sql
-- Description: Complete database setup including tables and default admin
-- Date: 2026-06-20
-- ============================================================

-- Create database
CREATE DATABASE IF NOT EXISTS attendance_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- Use the database
USE attendance_db;

-- ============================================================
-- TABLE: departments
-- Description: Stores department/division information
-- ============================================================
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL COMMENT 'Nama departemen/divisi',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu data dibuat'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabel data departemen';

-- ============================================================
-- TABLE: employees
-- Description: Stores employee information
-- ============================================================
CREATE TABLE IF NOT EXISTS employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nip VARCHAR(30) UNIQUE NOT NULL COMMENT 'Nomor Induk Pegawai',
    name VARCHAR(100) NOT NULL COMMENT 'Nama lengkap',
    department_id INT DEFAULT NULL COMMENT 'ID departemen (foreign key)',
    email VARCHAR(120) DEFAULT NULL COMMENT 'Email karyawan',
    gender ENUM('L', 'P') NOT NULL COMMENT 'Jenis kelamin: L=Laki-laki, P=Perempuan',
    is_active TINYINT(1) DEFAULT 1 COMMENT 'Status aktif: 1=aktif, 0=nonaktif',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu data dibuat',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Waktu data diperbarui',
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL,
    INDEX idx_nip (nip),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabel data karyawan';

-- ============================================================
-- TABLE: face_samples
-- Description: Stores face sample image paths
-- ============================================================
CREATE TABLE IF NOT EXISTS face_samples (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL COMMENT 'ID karyawan (foreign key)',
    image_path VARCHAR(255) NOT NULL COMMENT 'Path file gambar wajah',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu sampel dibuat',
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    INDEX idx_employee_id (employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabel sampel wajah karyawan';

-- ============================================================
-- TABLE: attendance
-- Description: Stores attendance records
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL COMMENT 'ID karyawan (foreign key)',
    attendance_date DATE NOT NULL COMMENT 'Tanggal absensi',
    check_in_time TIME NOT NULL COMMENT 'Jam masuk',
    check_out_time TIME DEFAULT NULL COMMENT 'Jam pulang',
    status ENUM('Hadir', 'Terlambat') NOT NULL COMMENT 'Status kehadiran',
    confidence DECIMAL(8,2) DEFAULT NULL COMMENT 'Nilai confidence dari face recognition',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu record dibuat',
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    UNIQUE KEY unique_attendance (employee_id, attendance_date) COMMENT 'Mencegah absensi ganda per hari',
    INDEX idx_attendance_date (attendance_date),
    INDEX idx_employee_date (employee_id, attendance_date)
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
    employee_id INT DEFAULT NULL COMMENT 'Link ke employees table (untuk role user)',
    is_active TINYINT(1) DEFAULT 1 COMMENT 'Status aktif: 1=aktif, 0=nonaktif',
    last_login TIMESTAMP NULL DEFAULT NULL COMMENT 'Waktu login terakhir',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu akun dibuat',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Waktu data diperbarui',
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL,
    INDEX idx_username (username),
    INDEX idx_role (role),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabel user untuk autentikasi sistem';

-- ============================================================
-- TABLE: activity_logs
-- Description: Stores system activity logs
-- ============================================================
CREATE TABLE IF NOT EXISTS activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT DEFAULT NULL COMMENT 'ID user pelaku (nullable)',
    username VARCHAR(50) DEFAULT NULL COMMENT 'Username pelaku saat aksi terjadi',
    action VARCHAR(100) NOT NULL COMMENT 'Jenis aksi (login, tambah_karyawan, dll)',
    detail VARCHAR(255) DEFAULT NULL COMMENT 'Detail tambahan aksi',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu aksi',
    INDEX idx_created_at (created_at),
    INDEX idx_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabel log aktivitas sistem';

-- ============================================================
-- VIEWS (Optional - Useful for reporting)
-- ============================================================

-- View: Daily attendance summary
CREATE OR REPLACE VIEW v_daily_attendance AS
SELECT
    a.attendance_date,
    COUNT(DISTINCT a.employee_id) as total_hadir,
    SUM(CASE WHEN a.status = 'Hadir' THEN 1 ELSE 0 END) as tepat_waktu,
    SUM(CASE WHEN a.status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat
FROM attendance a
GROUP BY a.attendance_date
ORDER BY a.attendance_date DESC;

-- View: Employee attendance detail
CREATE OR REPLACE VIEW v_employee_attendance AS
SELECT
    e.nip,
    e.name,
    d.name as department_name,
    e.gender,
    a.attendance_date,
    a.check_in_time,
    a.check_out_time,
    a.status,
    a.confidence
FROM employees e
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN attendance a ON e.id = a.employee_id
WHERE e.is_active = 1
ORDER BY a.attendance_date DESC, a.check_in_time ASC;

-- View: Employee attendance statistics
CREATE OR REPLACE VIEW v_employee_stats AS
SELECT
    e.id,
    e.nip,
    e.name,
    d.name as department_name,
    COUNT(a.id) as total_kehadiran,
    SUM(CASE WHEN a.status = 'Hadir' THEN 1 ELSE 0 END) as hadir_tepat_waktu,
    SUM(CASE WHEN a.status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat,
    ROUND(AVG(a.confidence), 2) as avg_confidence
FROM employees e
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN attendance a ON e.id = a.employee_id
WHERE e.is_active = 1
GROUP BY e.id, e.nip, e.name, d.name
ORDER BY e.name;

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
        e.nip,
        e.name,
        d.name as department_name,
        a.attendance_date,
        a.check_in_time,
        a.check_out_time,
        a.status,
        a.confidence
    FROM attendance a
    INNER JOIN employees e ON a.employee_id = e.id
    LEFT JOIN departments d ON e.department_id = d.id
    WHERE a.attendance_date BETWEEN start_date AND end_date
    ORDER BY a.attendance_date DESC, a.check_in_time ASC;
END //
DELIMITER ;

-- Procedure: Get employee attendance summary
DELIMITER //
CREATE PROCEDURE sp_employee_summary(
    IN employee_nip VARCHAR(30)
)
BEGIN
    SELECT
        e.nip,
        e.name,
        d.name as department_name,
        COUNT(a.id) as total_kehadiran,
        SUM(CASE WHEN a.status = 'Hadir' THEN 1 ELSE 0 END) as hadir,
        SUM(CASE WHEN a.status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat,
        MIN(a.attendance_date) as first_attendance,
        MAX(a.attendance_date) as last_attendance
    FROM employees e
    LEFT JOIN attendance a ON e.id = a.employee_id
    LEFT JOIN departments d ON e.department_id = d.id
    WHERE e.nip = employee_nip
    GROUP BY e.id, e.nip, e.name, d.name;
END //
DELIMITER ;

-- ============================================================
-- DEFAULT ADMIN ACCOUNT
-- ============================================================
-- Password: admin123 (hashed dengan bcrypt)
-- IMPORTANT: Ganti password ini setelah login pertama kali!
INSERT INTO users (username, password, full_name, role, is_active) VALUES
('admin', '$2b$12$m27ajAEcvmyjnMXCHbOu8efAI4cp3wTtyAIqB2KJVz/yLayZfTKH2', 'Administrator', 'admin', 1)
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
-- - SELECT * FROM v_employee_stats;
-- - CALL sp_get_attendance_by_date('2026-01-01', '2026-12-31');
-- ============================================================
