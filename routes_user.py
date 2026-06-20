"""
User routes for Flask web application
User dashboard and personal attendance features
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from src.auth_web import user_required, get_current_user, change_password
from src.database import get_db_connection
from mysql.connector import Error
from datetime import datetime, timedelta

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/dashboard')
@user_required
def dashboard():
    """User dashboard"""
    user = get_current_user()

    if not user['employee_id']:
        flash('Akun Anda tidak terhubung dengan data karyawan', 'warning')
        return render_template('user/dashboard.html', user=user, employee=None)

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return render_template('user/dashboard.html', user=user, employee=None)

    try:
        cursor = connection.cursor(dictionary=True)

        # Get employee info
        cursor.execute("""
            SELECT e.nip, e.name, d.name AS department_name, e.gender
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE e.id = %s
        """, (user['employee_id'],))
        employee = cursor.fetchone()

        # Get attendance statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_kehadiran,
                SUM(CASE WHEN status = 'Hadir' THEN 1 ELSE 0 END) as hadir_tepat_waktu,
                SUM(CASE WHEN status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat
            FROM attendance
            WHERE employee_id = %s
        """, (user['employee_id'],))
        stats = cursor.fetchone()

        # Get this month attendance
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM attendance
            WHERE employee_id = %s
            AND MONTH(attendance_date) = MONTH(CURDATE())
            AND YEAR(attendance_date) = YEAR(CURDATE())
        """, (user['employee_id'],))
        monthly = cursor.fetchone()

        # Status kehadiran hari ini (jam masuk & pulang)
        cursor.execute("""
            SELECT check_in_time, check_out_time, status
            FROM attendance
            WHERE employee_id = %s AND attendance_date = CURDATE()
        """, (user['employee_id'],))
        today = cursor.fetchone()

        # Persentase kehadiran: hari hadir dibanding total hari kerja sejak absensi pertama
        cursor.execute("""
            SELECT
                COUNT(*) as hari_hadir,
                DATEDIFF(CURDATE(), MIN(attendance_date)) + 1 as rentang_hari
            FROM attendance
            WHERE employee_id = %s
        """, (user['employee_id'],))
        rate_row = cursor.fetchone()
        if rate_row and rate_row['rentang_hari']:
            attendance_rate = round((rate_row['hari_hadir'] / rate_row['rentang_hari']) * 100, 1)
        else:
            attendance_rate = 0

        # Get recent attendance
        cursor.execute("""
            SELECT attendance_date, check_in_time, check_out_time, status, confidence
            FROM attendance
            WHERE employee_id = %s
            ORDER BY attendance_date DESC
            LIMIT 5
        """, (user['employee_id'],))
        recent = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('user/dashboard.html',
                             user=user,
                             employee=employee,
                             stats=stats,
                             monthly=monthly,
                             today=today,
                             attendance_rate=attendance_rate,
                             recent=recent)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('user/dashboard.html', user=user, employee=None)

@user_bp.route('/profile')
@user_required
def profile():
    """View user profile"""
    user = get_current_user()

    if not user['employee_id']:
        flash('Akun Anda tidak terhubung dengan data karyawan', 'warning')
        return render_template('user/profile.html', user=user, employee=None)

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return render_template('user/profile.html', user=user, employee=None)

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT e.nip, e.name, d.name AS department_name, e.email, e.gender, e.is_active, e.created_at
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE e.id = %s
        """, (user['employee_id'],))
        employee = cursor.fetchone()

        cursor.close()
        connection.close()

        return render_template('user/profile.html', user=user, employee=employee)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('user/profile.html', user=user, employee=None)

@user_bp.route('/attendance')
@user_required
def attendance():
    """View attendance history"""
    user = get_current_user()

    if not user['employee_id']:
        flash('Akun Anda tidak terhubung dengan data karyawan', 'warning')
        return render_template('user/attendance_history.html', user=user, records=[])

    # Get filter parameters
    filter_type = request.args.get('filter', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return render_template('user/attendance_history.html', user=user, records=[])

    try:
        cursor = connection.cursor(dictionary=True)

        # Build query based on filter
        if filter_type == '7days':
            query = """
                SELECT attendance_date, check_in_time, check_out_time, status, confidence
                FROM attendance
                WHERE employee_id = %s AND attendance_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                ORDER BY attendance_date DESC
            """
            cursor.execute(query, (user['employee_id'],))
        elif filter_type == '30days':
            query = """
                SELECT attendance_date, check_in_time, check_out_time, status, confidence
                FROM attendance
                WHERE employee_id = %s AND attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                ORDER BY attendance_date DESC
            """
            cursor.execute(query, (user['employee_id'],))
        elif filter_type == 'custom' and start_date and end_date:
            query = """
                SELECT attendance_date, check_in_time, check_out_time, status, confidence
                FROM attendance
                WHERE employee_id = %s AND attendance_date BETWEEN %s AND %s
                ORDER BY attendance_date DESC
            """
            cursor.execute(query, (user['employee_id'], start_date, end_date))
        else:
            query = """
                SELECT attendance_date, check_in_time, check_out_time, status, confidence
                FROM attendance
                WHERE employee_id = %s
                ORDER BY attendance_date DESC
            """
            cursor.execute(query, (user['employee_id'],))

        records = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('user/attendance_history.html',
                             user=user,
                             records=records,
                             filter_type=filter_type,
                             start_date=start_date,
                             end_date=end_date)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('user/attendance_history.html', user=user, records=[])

@user_bp.route('/statistics')
@user_required
def statistics():
    """View attendance statistics"""
    user = get_current_user()

    if not user['employee_id']:
        flash('Akun Anda tidak terhubung dengan data karyawan', 'warning')
        return render_template('user/statistics.html', user=user, stats=None)

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return render_template('user/statistics.html', user=user, stats=None)

    try:
        cursor = connection.cursor(dictionary=True)

        # Overall statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_kehadiran,
                SUM(CASE WHEN status = 'Hadir' THEN 1 ELSE 0 END) as hadir_tepat_waktu,
                SUM(CASE WHEN status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat,
                AVG(confidence) as avg_confidence,
                MIN(attendance_date) as first_attendance,
                MAX(attendance_date) as last_attendance
            FROM attendance
            WHERE employee_id = %s
        """, (user['employee_id'],))
        overall = cursor.fetchone()

        # Monthly statistics for current year
        cursor.execute("""
            SELECT
                MONTH(attendance_date) as bulan,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Hadir' THEN 1 ELSE 0 END) as hadir,
                SUM(CASE WHEN status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat
            FROM attendance
            WHERE employee_id = %s AND YEAR(attendance_date) = YEAR(CURDATE())
            GROUP BY MONTH(attendance_date)
            ORDER BY bulan
        """, (user['employee_id'],))
        monthly_stats = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('user/statistics.html',
                             user=user,
                             overall=overall,
                             monthly_stats=monthly_stats)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return render_template('user/statistics.html', user=user, stats=None)

@user_bp.route('/change-password', methods=['GET', 'POST'])
@user_required
def change_password_page():
    """Change password page"""
    user = get_current_user()

    if request.method == 'POST':
        old_password = request.form.get('old_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not old_password or not new_password:
            flash('Password tidak boleh kosong', 'danger')
            return redirect(url_for('user.change_password_page'))

        if new_password != confirm_password:
            flash('Password baru tidak cocok', 'danger')
            return redirect(url_for('user.change_password_page'))

        if len(new_password) < 6:
            flash('Password minimal 6 karakter', 'danger')
            return redirect(url_for('user.change_password_page'))

        success, message = change_password(user['id'], old_password, new_password)

        if success:
            flash(message, 'success')
            return redirect(url_for('user.dashboard'))
        else:
            flash(message, 'danger')
            return redirect(url_for('user.change_password_page'))

    return render_template('user/change_password.html', user=user)

@user_bp.route('/register')
@user_required
def register():
    """Registration page for employees"""
    user = get_current_user()
    return render_template('user/register.html', user=user)

@user_bp.route('/do-attendance')
@user_required
def do_attendance():
    """Face recognition attendance page for employees"""
    user = get_current_user()
    return render_template('user/do_attendance.html', user=user)
