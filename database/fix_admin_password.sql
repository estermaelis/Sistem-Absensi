-- ============================================================
-- FIX ADMIN PASSWORD
-- ============================================================
-- File: fix_admin_password.sql
-- Description: Update admin password dengan hash yang benar
-- Date: 2026-05-31
-- ============================================================

USE attendance_db;

-- Update password admin dengan hash yang benar
-- Password: admin123
UPDATE users
SET password = '$2b$12$eyUirMKnMvuGHdpmsQbqt.TmZH0Dnzqgb8KH0vQNF1lOTs2ay97aK'
WHERE username = 'admin';

-- Verifikasi
SELECT username, full_name, role, is_active
FROM users
WHERE username = 'admin';

-- ============================================================
-- SELESAI
-- ============================================================
-- Password admin berhasil diupdate!
--
-- Login dengan:
-- Username: admin
-- Password: admin123
-- ============================================================
