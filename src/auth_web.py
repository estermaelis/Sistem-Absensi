"""
Web Authentication module for Flask
Handles user login, logout, and session management for web interface
"""
from functools import wraps
from flask import session, redirect, url_for, flash
import bcrypt
from src.database import get_db_connection
from datetime import datetime

def hash_password(password):
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password, hashed_password):
    """Verify password against hashed password"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def authenticate_user(username, password):
    """
    Authenticate user with username and password
    Returns: (success, message, user_data)
    """
    connection = get_db_connection()
    if connection is None:
        return False, "Koneksi database gagal", None

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT id, username, password, full_name, role, student_id, is_active
            FROM users
            WHERE username = %s
        """
        cursor.execute(query, (username,))
        user = cursor.fetchone()

        if user is None:
            return False, "Username tidak ditemukan", None

        if user['is_active'] == 0:
            return False, "Akun tidak aktif", None

        if not verify_password(password, user['password']):
            return False, "Password salah", None

        # Update last login
        update_query = "UPDATE users SET last_login = %s WHERE id = %s"
        cursor.execute(update_query, (datetime.now(), user['id']))
        connection.commit()

        user.pop('password')

        cursor.close()
        connection.close()

        return True, "Login berhasil", user

    except Exception as e:
        print(f"Error during authentication: {e}")
        return False, f"Error: {e}", None

def login_user(user_data):
    """Set session data after successful login"""
    session['user_id'] = user_data['id']
    session['username'] = user_data['username']
    session['full_name'] = user_data['full_name']
    session['role'] = user_data['role']
    session['student_id'] = user_data['student_id']
    session['is_authenticated'] = True

def logout_user():
    """Clear session data"""
    session.clear()

def is_authenticated():
    """Check if user is authenticated"""
    return session.get('is_authenticated', False)

def is_admin():
    """Check if current user is admin"""
    return is_authenticated() and session.get('role') == 'admin'

def is_user():
    """Check if current user is regular user"""
    return is_authenticated() and session.get('role') == 'user'

def get_current_user():
    """Get current user data from session"""
    if not is_authenticated():
        return None
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'full_name': session.get('full_name'),
        'role': session.get('role'),
        'student_id': session.get('student_id')
    }

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Silakan login terlebih dahulu', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Silakan login terlebih dahulu', 'warning')
            return redirect(url_for('login'))
        if not is_admin():
            flash('Akses ditolak. Hanya admin yang dapat mengakses halaman ini', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    """Decorator to require user role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Silakan login terlebih dahulu', 'warning')
            return redirect(url_for('login'))
        if not is_user():
            flash('Akses ditolak. Halaman ini hanya untuk user biasa', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def create_user(username, password, full_name, role='user', student_id=None):
    """
    Create new user account
    Returns: (success, message)
    """
    connection = get_db_connection()
    if connection is None:
        return False, "Koneksi database gagal"

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return False, "Username sudah digunakan"

        hashed_pw = hash_password(password)

        query = """
            INSERT INTO users (username, password, full_name, role, student_id)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (username, hashed_pw, full_name, role, student_id))
        connection.commit()

        cursor.close()
        connection.close()

        return True, "User berhasil dibuat"

    except Exception as e:
        print(f"Error creating user: {e}")
        return False, f"Error: {e}"

def change_password(user_id, old_password, new_password):
    """
    Change user password
    Returns: (success, message)
    """
    connection = get_db_connection()
    if connection is None:
        return False, "Koneksi database gagal"

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            return False, "User tidak ditemukan"

        if not verify_password(old_password, user['password']):
            return False, "Password lama salah"

        hashed_pw = hash_password(new_password)

        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_pw, user_id))
        connection.commit()

        cursor.close()
        connection.close()

        return True, "Password berhasil diubah"

    except Exception as e:
        print(f"Error changing password: {e}")
        return False, f"Error: {e}"

def reset_user_password(user_id, new_password):
    """
    Reset user password (admin function)
    Returns: (success, message)
    """
    connection = get_db_connection()
    if connection is None:
        return False, "Koneksi database gagal"

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            return False, "User tidak ditemukan"

        hashed_pw = hash_password(new_password)

        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_pw, user_id))
        connection.commit()

        cursor.close()
        connection.close()

        return True, "Password berhasil direset"

    except Exception as e:
        print(f"Error resetting password: {e}")
        return False, f"Error: {e}"
