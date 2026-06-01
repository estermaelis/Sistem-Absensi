"""
Admin routes for Flask web application
Part 1: Student management routes
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from src.auth_web import admin_required, get_current_user
from src.database import get_db_connection
from mysql.connector import Error

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard"""
    user = get_current_user()

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('index'))

    try:
        cursor = connection.cursor(dictionary=True)

        # Get statistics
        cursor.execute("SELECT COUNT(*) as total FROM students WHERE is_active = 1")
        total_students = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM users WHERE is_active = 1")
        total_users = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM attendance WHERE attendance_date = CURDATE()")
        today_attendance = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COUNT(DISTINCT student_id) as total
            FROM attendance
            WHERE MONTH(attendance_date) = MONTH(CURDATE())
            AND YEAR(attendance_date) = YEAR(CURDATE())
        """)
        monthly_attendance = cursor.fetchone()['total']

        cursor.close()
        connection.close()

        return render_template('admin/dashboard.html',
                             user=user,
                             total_students=total_students,
                             total_users=total_users,
                             today_attendance=today_attendance,
                             monthly_attendance=monthly_attendance)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('index'))

@admin_bp.route('/students')
@admin_required
def students():
    """List all students"""
    user = get_current_user()

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('admin.dashboard'))

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nis, name, class_name, gender, is_active, created_at
            FROM students
            ORDER BY created_at DESC
        """)
        students_list = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('admin/students.html', user=user, students=students_list)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/students/search')
@admin_required
def search_students():
    """Search students"""
    keyword = request.args.get('q', '').strip()
    user = get_current_user()

    if not keyword:
        return redirect(url_for('admin.students'))

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('admin.students'))

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT id, nis, name, class_name, gender, is_active, created_at
            FROM students
            WHERE nis LIKE %s OR name LIKE %s
            ORDER BY name
        """
        search_pattern = f"%{keyword}%"
        cursor.execute(query, (search_pattern, search_pattern))
        students_list = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('admin/students.html',
                             user=user,
                             students=students_list,
                             search_keyword=keyword)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_student(student_id):
    """Edit student"""
    user = get_current_user()

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('admin.students'))

    try:
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            nis = request.form.get('nis', '').strip()
            name = request.form.get('name', '').strip()
            class_name = request.form.get('class_name', '').strip()
            gender = request.form.get('gender', '').strip().upper()

            if not nis or not name or not gender:
                flash('Data tidak lengkap', 'danger')
                return redirect(url_for('admin.edit_student', student_id=student_id))

            if gender not in ['L', 'P']:
                flash('Jenis kelamin harus L atau P', 'danger')
                return redirect(url_for('admin.edit_student', student_id=student_id))

            update_query = """
                UPDATE students
                SET nis = %s, name = %s, class_name = %s, gender = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (nis, name, class_name, gender, student_id))
            connection.commit()

            flash('Data siswa berhasil diupdate', 'success')
            cursor.close()
            connection.close()
            return redirect(url_for('admin.students'))

        # GET request
        cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            flash('Siswa tidak ditemukan', 'danger')
            cursor.close()
            connection.close()
            return redirect(url_for('admin.students'))

        cursor.close()
        connection.close()

        return render_template('admin/edit_student.html', user=user, student=student)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/students/<int:student_id>/toggle', methods=['POST'])
@admin_required
def toggle_student_status(student_id):
    """Toggle student active status"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Koneksi database gagal'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, is_active FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            return jsonify({'success': False, 'message': 'Siswa tidak ditemukan'}), 404

        new_status = 0 if student['is_active'] else 1
        cursor.execute("UPDATE students SET is_active = %s WHERE id = %s", (new_status, student_id))
        connection.commit()

        cursor.close()
        connection.close()

        status_text = "Aktif" if new_status else "Nonaktif"
        return jsonify({'success': True, 'message': f'Status berhasil diubah menjadi {status_text}', 'new_status': new_status})
    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500

@admin_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@admin_required
def delete_student(student_id):
    """Delete student"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Koneksi database gagal'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, name FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            return jsonify({'success': False, 'message': 'Siswa tidak ditemukan'}), 404

        cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({'success': True, 'message': f"Siswa {student['name']} berhasil dihapus"})
    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
