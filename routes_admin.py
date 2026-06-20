"""
Admin routes for Flask web application
Part 1: Student management routes
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from src.auth_web import admin_required, get_current_user
from src.database import get_db_connection
from src.activity_log import log_activity
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
        cursor.execute("SELECT COUNT(*) as total FROM employees WHERE is_active = 1")
        total_employees = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM users WHERE is_active = 1")
        total_users = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM departments")
        total_departments = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM attendance WHERE attendance_date = CURDATE()")
        today_attendance = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM attendance WHERE attendance_date = CURDATE() AND status = 'Terlambat'")
        today_late = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COUNT(DISTINCT employee_id) as total
            FROM attendance
            WHERE MONTH(attendance_date) = MONTH(CURDATE())
            AND YEAR(attendance_date) = YEAR(CURDATE())
        """)
        monthly_attendance = cursor.fetchone()['total']

        # Tidak hadir hari ini & persentase kehadiran
        today_absent = max(total_employees - today_attendance, 0)
        attendance_rate = round((today_attendance / total_employees) * 100, 1) if total_employees else 0

        # Aktivitas terbaru
        cursor.execute("""
            SELECT username, action, detail, created_at
            FROM activity_logs
            ORDER BY created_at DESC
            LIMIT 8
        """)
        recent_activities = cursor.fetchall()

        # Data grafik kehadiran bulan berjalan (per hari: hadir vs terlambat)
        cursor.execute("""
            SELECT DAY(attendance_date) as hari,
                   SUM(CASE WHEN status = 'Hadir' THEN 1 ELSE 0 END) as hadir,
                   SUM(CASE WHEN status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat
            FROM attendance
            WHERE MONTH(attendance_date) = MONTH(CURDATE())
            AND YEAR(attendance_date) = YEAR(CURDATE())
            GROUP BY DAY(attendance_date)
            ORDER BY hari
        """)
        chart_rows = cursor.fetchall()
        chart_labels = [row['hari'] for row in chart_rows]
        chart_hadir = [int(row['hadir']) for row in chart_rows]
        chart_terlambat = [int(row['terlambat']) for row in chart_rows]

        cursor.close()
        connection.close()

        return render_template('admin/dashboard.html',
                             user=user,
                             total_employees=total_employees,
                             total_users=total_users,
                             total_departments=total_departments,
                             today_attendance=today_attendance,
                             today_late=today_late,
                             monthly_attendance=monthly_attendance,
                             today_absent=today_absent,
                             attendance_rate=attendance_rate,
                             recent_activities=recent_activities,
                             chart_labels=chart_labels,
                             chart_hadir=chart_hadir,
                             chart_terlambat=chart_terlambat)
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
            SELECT e.id, e.nip, e.name, d.name AS department_name, e.gender, e.is_active, e.created_at
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            ORDER BY e.created_at DESC
        """)
        employees_list = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('admin/students.html', user=user, employees=employees_list)
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
            SELECT e.id, e.nip, e.name, d.name AS department_name, e.gender, e.is_active, e.created_at
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE e.nip LIKE %s OR e.name LIKE %s
            ORDER BY e.name
        """
        search_pattern = f"%{keyword}%"
        cursor.execute(query, (search_pattern, search_pattern))
        employees_list = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('admin/students.html',
                             user=user,
                             employees=employees_list,
                             search_keyword=keyword)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_student(student_id):
    """Edit employee"""
    user = get_current_user()

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('admin.students'))

    try:
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            nip = request.form.get('nip', '').strip()
            name = request.form.get('name', '').strip()
            department_id = request.form.get('department_id') or None
            email = request.form.get('email', '').strip() or None
            gender = request.form.get('gender', '').strip().upper()

            if not nip or not name or not gender:
                flash('Data tidak lengkap', 'danger')
                return redirect(url_for('admin.edit_student', student_id=student_id))

            if gender not in ['L', 'P']:
                flash('Jenis kelamin harus L atau P', 'danger')
                return redirect(url_for('admin.edit_student', student_id=student_id))

            update_query = """
                UPDATE employees
                SET nip = %s, name = %s, department_id = %s, email = %s, gender = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (nip, name, department_id, email, gender, student_id))
            connection.commit()

            log_activity(user['id'], user['username'], 'edit_karyawan', f'Karyawan: {name} (NIP {nip})')
            flash('Data karyawan berhasil diupdate', 'success')
            cursor.close()
            connection.close()
            return redirect(url_for('admin.students'))

        # GET request
        cursor.execute("SELECT * FROM employees WHERE id = %s", (student_id,))
        employee = cursor.fetchone()

        if not employee:
            flash('Karyawan tidak ditemukan', 'danger')
            cursor.close()
            connection.close()
            return redirect(url_for('admin.students'))

        cursor.execute("SELECT id, name FROM departments ORDER BY name")
        departments = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('admin/edit_employee.html', user=user, employee=employee, departments=departments)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/students/<int:student_id>/toggle', methods=['POST'])
@admin_required
def toggle_student_status(student_id):
    """Toggle employee active status"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Koneksi database gagal'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, is_active FROM employees WHERE id = %s", (student_id,))
        employee = cursor.fetchone()

        if not employee:
            return jsonify({'success': False, 'message': 'Karyawan tidak ditemukan'}), 404

        new_status = 0 if employee['is_active'] else 1
        cursor.execute("UPDATE employees SET is_active = %s WHERE id = %s", (new_status, student_id))
        connection.commit()

        cursor.close()
        connection.close()

        status_text = "Aktif" if new_status else "Nonaktif"
        u = get_current_user()
        log_activity(u['id'], u['username'], 'toggle_karyawan', f'Karyawan ID {student_id} -> {status_text}')
        return jsonify({'success': True, 'message': f'Status berhasil diubah menjadi {status_text}', 'new_status': new_status})
    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500

@admin_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@admin_required
def delete_student(student_id):
    """Delete employee"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Koneksi database gagal'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, name FROM employees WHERE id = %s", (student_id,))
        employee = cursor.fetchone()

        if not employee:
            return jsonify({'success': False, 'message': 'Karyawan tidak ditemukan'}), 404

        cursor.execute("DELETE FROM employees WHERE id = %s", (student_id,))
        connection.commit()

        cursor.close()
        connection.close()

        u = get_current_user()
        log_activity(u['id'], u['username'], 'hapus_karyawan', f"Karyawan: {employee['name']}")
        return jsonify({'success': True, 'message': f"Karyawan {employee['name']} berhasil dihapus"})
    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
