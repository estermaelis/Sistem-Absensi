-- ============================================================
-- MIGRATION: Sistem Absensi Siswa -> Karyawan
-- ============================================================
-- File: migration_to_employees.sql
-- Deskripsi: Rename skema students->employees (NON-DESTRUKTIF via ALTER).
--            Data, ID, sampel wajah, dan model terlatih tetap utuh.
-- PENTING: BACKUP database dulu sebelum menjalankan:
--          mysqldump -u root -p attendance_db > backup.sql
-- ============================================================

USE attendance_db;

-- ------------------------------------------------------------
-- 1. Tabel departments
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL COMMENT 'Nama departemen/divisi',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabel data departemen';

-- ------------------------------------------------------------
-- 2. Migrasi nilai class_name lama -> baris departments
-- ------------------------------------------------------------
INSERT IGNORE INTO departments (name)
SELECT DISTINCT TRIM(class_name)
FROM students
WHERE class_name IS NOT NULL AND TRIM(class_name) <> '';

-- ------------------------------------------------------------
-- 3. students: tambah department_id, backfill, drop class_name
-- ------------------------------------------------------------
ALTER TABLE students ADD COLUMN department_id INT NULL AFTER name;

UPDATE students s
JOIN departments d ON TRIM(s.class_name) = d.name
SET s.department_id = d.id;

ALTER TABLE students
    ADD CONSTRAINT fk_students_department
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL;

ALTER TABLE students DROP COLUMN class_name;

-- ------------------------------------------------------------
-- 4. students: tambah email opsional
-- ------------------------------------------------------------
ALTER TABLE students ADD COLUMN email VARCHAR(120) NULL AFTER department_id;

-- ------------------------------------------------------------
-- 5. Rename kolom nis->nip, lalu rename tabel students->employees
-- ------------------------------------------------------------
ALTER TABLE students CHANGE nis nip VARCHAR(30) NOT NULL COMMENT 'Nomor Induk Pegawai';

-- Drop FK dari tabel anak dulu agar RENAME tidak gagal
ALTER TABLE face_samples DROP FOREIGN KEY face_samples_ibfk_1;
ALTER TABLE attendance DROP FOREIGN KEY attendance_ibfk_1;
ALTER TABLE users DROP FOREIGN KEY users_ibfk_1;

RENAME TABLE students TO employees;

-- ------------------------------------------------------------
-- 6. face_samples: student_id -> employee_id (+ FK baru)
-- ------------------------------------------------------------
ALTER TABLE face_samples CHANGE student_id employee_id INT NOT NULL COMMENT 'ID karyawan (foreign key)';
ALTER TABLE face_samples
    ADD CONSTRAINT fk_face_samples_employee
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE;

-- ------------------------------------------------------------
-- 7. attendance: student_id -> employee_id, tambah check_out_time
-- ------------------------------------------------------------
ALTER TABLE attendance CHANGE student_id employee_id INT NOT NULL COMMENT 'ID karyawan (foreign key)';
ALTER TABLE attendance ADD COLUMN check_out_time TIME NULL COMMENT 'Jam pulang' AFTER check_in_time;
ALTER TABLE attendance
    ADD CONSTRAINT fk_attendance_employee
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE;

-- ------------------------------------------------------------
-- 8. users: student_id -> employee_id (+ FK baru)
-- ------------------------------------------------------------
ALTER TABLE users CHANGE student_id employee_id INT DEFAULT NULL COMMENT 'Link ke employees table (untuk role user)';
ALTER TABLE users
    ADD CONSTRAINT fk_users_employee
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL;

-- ------------------------------------------------------------
-- 9. Drop & recreate views/procedures lama
-- ------------------------------------------------------------
DROP VIEW IF EXISTS v_daily_attendance;
DROP VIEW IF EXISTS v_student_attendance;
DROP VIEW IF EXISTS v_student_stats;
DROP PROCEDURE IF EXISTS sp_get_attendance_by_date;
DROP PROCEDURE IF EXISTS sp_student_summary;

CREATE OR REPLACE VIEW v_daily_attendance AS
SELECT
    a.attendance_date,
    COUNT(DISTINCT a.employee_id) as total_hadir,
    SUM(CASE WHEN a.status = 'Hadir' THEN 1 ELSE 0 END) as tepat_waktu,
    SUM(CASE WHEN a.status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat
FROM attendance a
GROUP BY a.attendance_date
ORDER BY a.attendance_date DESC;

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
-- SELESAI
-- Verifikasi:
--   SHOW TABLES;
--   DESCRIBE employees;
--   SELECT * FROM departments;
--   SELECT COUNT(*) FROM face_samples;
--   SELECT COUNT(*) FROM attendance;
-- ============================================================
SELECT 'Migrasi ke skema employees selesai!' as Status;
