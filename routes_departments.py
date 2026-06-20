"""
Admin routes for department management (Kelola Departemen)
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from src.auth_web import admin_required, get_current_user
from src.database import get_db_connection
from src.activity_log import log_activity
from mysql.connector import Error

departments_bp = Blueprint('departments', __name__, url_prefix='/admin/departments')


@departments_bp.route('/')
@admin_required
def index():
    """List all departments with employee counts"""
    user = get_current_user()

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('admin.dashboard'))

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT d.id, d.name, d.created_at, COUNT(e.id) AS employee_count
            FROM departments d
            LEFT JOIN employees e ON e.department_id = d.id
            GROUP BY d.id, d.name, d.created_at
            ORDER BY d.name
        """)
        departments = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('admin/departments.html', user=user, departments=departments)
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        return redirect(url_for('admin.dashboard'))


@departments_bp.route('/add', methods=['POST'])
@admin_required
def add():
    """Create a new department"""
    name = request.form.get('name', '').strip()

    if not name:
        flash('Nama departemen tidak boleh kosong', 'danger')
        return redirect(url_for('departments.index'))

    connection = get_db_connection()
    if connection is None:
        flash('Koneksi database gagal', 'danger')
        return redirect(url_for('departments.index'))

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM departments WHERE name = %s", (name,))
        if cursor.fetchone():
            flash(f'Departemen "{name}" sudah ada', 'danger')
        else:
            cursor.execute("INSERT INTO departments (name) VALUES (%s)", (name,))
            connection.commit()
            u = get_current_user()
            log_activity(u['id'], u['username'], 'tambah_departemen', f'Departemen: {name}')
            flash(f'Departemen "{name}" berhasil ditambahkan', 'success')
        cursor.close()
        connection.close()
    except Error as e:
        flash(f'Database error: {e}', 'danger')

    return redirect(url_for('departments.index'))


@departments_bp.route('/<int:department_id>/edit', methods=['POST'])
@admin_required
def edit(department_id):
    """Rename a department"""
    name = request.form.get('name', '').strip()

    if not name:
        return jsonify({'success': False, 'message': 'Nama departemen tidak boleh kosong'}), 400

    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Koneksi database gagal'}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id FROM departments WHERE name = %s AND id <> %s", (name, department_id))
        if cursor.fetchone():
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': f'Departemen "{name}" sudah ada'}), 400

        cursor.execute("UPDATE departments SET name = %s WHERE id = %s", (name, department_id))
        connection.commit()
        cursor.close()
        connection.close()
        u = get_current_user()
        log_activity(u['id'], u['username'], 'edit_departemen', f'Departemen ID {department_id} -> {name}')
        return jsonify({'success': True, 'message': 'Departemen berhasil diupdate', 'name': name})
    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500


@departments_bp.route('/<int:department_id>/delete', methods=['POST'])
@admin_required
def delete(department_id):
    """Delete a department (employees keep existing but department_id set NULL)"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Koneksi database gagal'}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM departments WHERE id = %s", (department_id,))
        department = cursor.fetchone()

        if not department:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Departemen tidak ditemukan'}), 404

        cursor.execute("DELETE FROM departments WHERE id = %s", (department_id,))
        connection.commit()
        cursor.close()
        connection.close()
        u = get_current_user()
        log_activity(u['id'], u['username'], 'hapus_departemen', f"Departemen: {department['name']}")
        return jsonify({'success': True, 'message': f"Departemen \"{department['name']}\" berhasil dihapus"})
    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
