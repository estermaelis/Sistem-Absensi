"""
Admin routes for Flask web application
Part 2: User management and reports routes
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file
from src.auth_web import admin_required, get_current_user, create_user, reset_user_password
from src.database import get_db_connection
from src.export_report import fetch_attendance_rows, build_csv, build_excel, build_pdf
from src.activity_log import log_activity
from mysql.connector import Error
from datetime import datetime, timedelta

admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin')

@admin_users_bp.route('/users')
@admin_required
def users():
    """List all users"""
    user = get_current_user()

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('admin.dashboard'))

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT u.id, u.username, u.full_name, u.role, u.is_active,
                   e.nip, e.name as employee_name, u.last_login
            FROM users u
            LEFT JOIN employees e ON u.employee_id = e.id
            ORDER BY u.role, u.username
        """
        cursor.execute(query)
        users_list = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('admin/users.html', user=user, users=users_list)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_users_bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Add new user"""
    user = get_current_user()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', '').strip()
        nip = request.form.get('nip', '').strip()

        # Validasi role
        if not role:
            flash('Role harus dipilih', 'danger')
            return redirect(url_for('admin_users.add_user'))

        if role not in ['admin', 'user']:
            flash('Role tidak valid', 'danger')
            return redirect(url_for('admin_users.add_user'))

        # Validasi password
        if not password:
            flash('Password harus diisi', 'danger')
            return redirect(url_for('admin_users.add_user'))

        if len(password) < 6:
            flash('Password minimal 6 karakter', 'danger')
            return redirect(url_for('admin_users.add_user'))

        # Untuk role user, gunakan NIP sebagai username
        employee_id = None
        if role == 'user':
            if not nip:
                flash('NIP harus dipilih untuk role User', 'danger')
                return redirect(url_for('admin_users.add_user'))

            # Ambil data karyawan dari database
            connection = get_db_connection()
            if not connection:
                flash('Koneksi database gagal', 'danger')
                return redirect(url_for('admin_users.add_user'))

            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT id, name FROM employees WHERE nip = %s", (nip,))
                employee = cursor.fetchone()
                cursor.close()
                connection.close()

                if not employee:
                    flash(f'NIP {nip} tidak ditemukan dalam data karyawan', 'danger')
                    return redirect(url_for('admin_users.add_user'))

                # Set username dan full_name dari data karyawan
                username = nip
                full_name = employee['name']
                employee_id = employee['id']

            except Error as e:
                flash(f'Database error: {e}', 'danger')
                return redirect(url_for('admin_users.add_user'))

        else:  # role == 'admin'
            # Untuk admin, validasi username dan full_name
            if not username:
                flash('Username harus diisi untuk role Admin', 'danger')
                return redirect(url_for('admin_users.add_user'))

            if not full_name:
                flash('Nama lengkap harus diisi untuk role Admin', 'danger')
                return redirect(url_for('admin_users.add_user'))

        # Buat user
        success, message = create_user(username, password, full_name, role, employee_id)

        if success:
            log_activity(user['id'], user['username'], 'tambah_user', f'User: {username} (role {role})')
            flash(message, 'success')
            return redirect(url_for('admin_users.users'))
        else:
            flash(message, 'danger')
            return redirect(url_for('admin_users.add_user'))

    # GET request
    connection = get_db_connection()
    employees_list = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT nip, name FROM employees WHERE is_active = 1 ORDER BY name")
            employees_list = cursor.fetchall()
            cursor.close()
            connection.close()
        except Error:
            pass

    return render_template('admin/add_user.html', user=user, employees=employees_list)

@admin_users_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_password(user_id):
    """Reset user password"""
    data = request.get_json()
    new_password = data.get('password', '').strip()

    if not new_password or len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password minimal 6 karakter'}), 400

    success, message = reset_user_password(user_id, new_password)

    if success:
        u = get_current_user()
        log_activity(u['id'], u['username'], 'reset_password', f'Reset password user ID {user_id}')
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 500

@admin_users_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Koneksi database gagal'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, is_active, role FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404

        if user_data['role'] == 'admin':
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin' AND is_active = 1")
            admin_count = cursor.fetchone()['count']
            if admin_count <= 1 and user_data['is_active'] == 1:
                return jsonify({'success': False, 'message': 'Tidak dapat menonaktifkan admin terakhir'}), 400

        new_status = 0 if user_data['is_active'] else 1
        cursor.execute("UPDATE users SET is_active = %s WHERE id = %s", (new_status, user_id))
        connection.commit()

        cursor.close()
        connection.close()

        status_text = "Aktif" if new_status else "Nonaktif"
        u = get_current_user()
        log_activity(u['id'], u['username'], 'toggle_user', f'User ID {user_id} -> {status_text}')
        return jsonify({'success': True, 'message': f'Status berhasil diubah menjadi {status_text}', 'new_status': new_status})
    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500

@admin_users_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Koneksi database gagal'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404

        if user_data['role'] == 'admin':
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin' AND is_active = 1")
            admin_count = cursor.fetchone()['count']
            if admin_count <= 1:
                return jsonify({'success': False, 'message': 'Tidak dapat menghapus admin terakhir'}), 400

        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        connection.commit()

        cursor.close()
        connection.close()

        u = get_current_user()
        log_activity(u['id'], u['username'], 'hapus_user', f"User: {user_data['username']}")
        return jsonify({'success': True, 'message': f"User {user_data['username']} berhasil dihapus"})
    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500

@admin_users_bp.route('/reports')
@admin_required
def reports():
    """View reports page"""
    user = get_current_user()
    return render_template('admin/reports.html', user=user)

@admin_users_bp.route('/activity-log')
@admin_required
def activity_log():
    """View system activity log"""
    user = get_current_user()

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('admin.dashboard'))

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, user_id, username, action, detail, created_at
            FROM activity_logs
            ORDER BY created_at DESC
            LIMIT 200
        """)
        logs = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('admin/activity_log.html', user=user, logs=logs)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_users_bp.route('/reports/export/<fmt>')
@admin_required
def export_report_route(fmt):
    """Export attendance report as csv, excel, or pdf"""
    start_date = request.args.get('start_date') or None
    end_date = request.args.get('end_date') or None

    if fmt not in ('csv', 'excel', 'pdf'):
        flash('Format export tidak valid', 'danger')
        return redirect(url_for('admin_users.reports'))

    try:
        rows = fetch_attendance_rows(start_date, end_date)
    except Exception as e:
        flash(f'Error mengambil data: {e}', 'danger')
        return redirect(url_for('admin_users.reports'))

    if not rows:
        flash('Tidak ada data absensi untuk diekspor', 'warning')
        return redirect(url_for('admin_users.reports'))

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if fmt == 'csv':
        buffer = build_csv(rows)
        return send_file(buffer, mimetype='text/csv', as_attachment=True,
                         download_name=f'laporan_absensi_{timestamp}.csv')
    elif fmt == 'excel':
        buffer = build_excel(rows)
        return send_file(buffer,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True,
                         download_name=f'laporan_absensi_{timestamp}.xlsx')
    else:  # pdf
        buffer = build_pdf(rows)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                         download_name=f'laporan_absensi_{timestamp}.pdf')

@admin_users_bp.route('/reports/daily')
@admin_required
def daily_report():
    """Daily attendance report"""
    user = get_current_user()
    report_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('admin_users.reports'))

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT e.nip, e.name, d.name AS department_name, a.check_in_time, a.check_out_time, a.status, a.confidence
            FROM attendance a
            INNER JOIN employees e ON a.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE a.attendance_date = %s
            ORDER BY a.check_in_time
        """
        cursor.execute(query, (report_date,))
        records = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('admin/daily_report.html',
                             user=user,
                             records=records,
                             report_date=report_date)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('admin_users.reports'))

@admin_users_bp.route('/reports/statistics')
@admin_required
def statistics():
    """View statistics"""
    user = get_current_user()

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('admin.dashboard'))

    try:
        cursor = connection.cursor(dictionary=True)

        # Overall statistics
        cursor.execute("""
            SELECT
                COUNT(DISTINCT employee_id) as total_karyawan_hadir,
                COUNT(*) as total_absensi,
                SUM(CASE WHEN status = 'Hadir' THEN 1 ELSE 0 END) as tepat_waktu,
                SUM(CASE WHEN status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat,
                AVG(confidence) as avg_confidence
            FROM attendance
        """)
        overall = cursor.fetchone()

        # Monthly statistics
        cursor.execute("""
            SELECT
                COUNT(DISTINCT employee_id) as karyawan_hadir,
                COUNT(*) as total_absensi,
                SUM(CASE WHEN status = 'Hadir' THEN 1 ELSE 0 END) as tepat_waktu,
                SUM(CASE WHEN status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat
            FROM attendance
            WHERE MONTH(attendance_date) = MONTH(CURDATE())
            AND YEAR(attendance_date) = YEAR(CURDATE())
        """)
        monthly = cursor.fetchone()

        # Top employees
        cursor.execute("""
            SELECT e.nip, e.name, COUNT(a.id) as total_hadir
            FROM employees e
            INNER JOIN attendance a ON e.id = a.employee_id
            GROUP BY e.id, e.nip, e.name
            ORDER BY total_hadir DESC
            LIMIT 5
        """)
        top_employees = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('admin/statistics.html',
                             user=user,
                             overall=overall,
                             monthly=monthly,
                             top_employees=top_employees)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('admin.dashboard'))
