from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, Response, session, flash
import cv2
import os
import numpy as np
from datetime import datetime, date
from dotenv import load_dotenv
from src.database import get_db_connection
from mysql.connector import Error
import base64
from io import BytesIO
from PIL import Image
from src.auth_web import authenticate_user, login_user, logout_user, is_authenticated, get_current_user, login_required, admin_required

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Register blueprints
from routes_admin import admin_bp
from routes_admin_users import admin_users_bp
from routes_user import user_bp

app.register_blueprint(admin_bp)
app.register_blueprint(admin_users_bp)
app.register_blueprint(user_bp)

# Global variables
camera = None
recognizer = None
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

@app.route('/')
def index():
    """Dashboard page - redirect to appropriate dashboard based on role"""
    if not is_authenticated():
        return redirect(url_for('login'))

    user = get_current_user()
    if user['role'] == 'admin':
        return redirect(url_for('admin.dashboard'))
    else:
        return redirect(url_for('user.dashboard'))

@app.route('/students')
@login_required
def students():
    """List all students"""
    connection = get_db_connection()
    if connection is None:
        return render_template('error.html', message="Database connection failed")

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

        return render_template('students.html', students=students_list)
    except Error as e:
        return render_template('error.html', message=f"Database error: {e}")

@app.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for student registration"""
    data = request.json

    nis = data.get('nis', '').strip()
    name = data.get('name', '').strip()
    class_name = data.get('class_name', '').strip()
    gender = data.get('gender', '').strip().upper()

    if not nis or not name or not gender:
        return jsonify({'success': False, 'message': 'Data tidak lengkap'}), 400

    if gender not in ['L', 'P']:
        return jsonify({'success': False, 'message': 'Jenis kelamin harus L atau P'}), 400

    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor()

        # Check if NIS exists
        cursor.execute("SELECT id FROM students WHERE nis = %s", (nis,))
        if cursor.fetchone():
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': f'NIS {nis} sudah terdaftar'}), 400

        # Insert student
        insert_query = "INSERT INTO students (nis, name, class_name, gender) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (nis, name, class_name, gender))
        connection.commit()
        student_id = cursor.lastrowid

        cursor.close()
        connection.close()

        return jsonify({'success': True, 'message': 'Siswa berhasil didaftarkan', 'student_id': student_id})

    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500

def generate_frames():
    """Generate video frames from camera"""
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)

    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Detect faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

            # Draw rectangles around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
@login_required
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/start_camera', methods=['POST'])
@login_required
def api_start_camera():
    """Start camera for face capture"""
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)

    if camera.isOpened():
        return jsonify({'success': True, 'message': 'Kamera berhasil diaktifkan'})
    else:
        return jsonify({'success': False, 'message': 'Gagal membuka kamera'}), 500

@app.route('/api/stop_camera', methods=['POST'])
@login_required
def api_stop_camera():
    """Stop camera"""
    global camera
    if camera is not None:
        camera.release()
        camera = None
    return jsonify({'success': True, 'message': 'Kamera dimatikan'})

@app.route('/api/capture_samples', methods=['POST'])
@login_required
def api_capture_samples():
    """API endpoint to capture face samples from server camera"""
    data = request.json
    student_id = data.get('student_id')

    if not student_id:
        return jsonify({'success': False, 'message': 'Student ID tidak ditemukan'}), 400

    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        return jsonify({'success': False, 'message': 'Gagal membuka kamera'}), 500

    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    try:
        # Create directory for student
        dataset_path = os.path.join('dataset', str(student_id))
        os.makedirs(dataset_path, exist_ok=True)

        cursor = connection.cursor()
        saved_count = 0
        max_samples = int(os.getenv('SAMPLES_PER_PERSON', 30))

        # Capture samples
        for i in range(max_samples):
            ret, frame = camera.read()
            if not ret:
                break

            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

            if len(faces) > 0:
                # Get first face
                (x, y, w, h) = faces[0]
                face_img = gray[y:y+h, x:x+w]

                # Save image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"sample_{i+1}_{timestamp}.jpg"
                filepath = os.path.join(dataset_path, filename)
                cv2.imwrite(filepath, face_img)

                # Save to database
                insert_query = "INSERT INTO face_samples (student_id, image_path) VALUES (%s, %s)"
                cursor.execute(insert_query, (student_id, filepath))
                saved_count += 1

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({'success': True, 'message': f'{saved_count} sampel berhasil disimpan', 'count': saved_count})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/train')
@login_required
def train():
    """Training page"""
    return render_template('train.html')

@app.route('/api/train', methods=['POST'])
@login_required
def api_train():
    """API endpoint to train model"""
    from src.train_model import train_model

    try:
        train_model()
        return jsonify({'success': True, 'message': 'Model berhasil dilatih'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/attendance')
@login_required
def attendance():
    """Attendance page"""
    return render_template('attendance.html')

@app.route('/api/attendance/today')
def api_attendance_today():
    """API endpoint to get today's attendance"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.nis, s.name,
                   TIME_FORMAT(a.check_in_time, '%H:%i:%s') as check_in_time,
                   a.status
            FROM attendance a
            INNER JOIN students s ON a.student_id = s.id
            WHERE a.attendance_date = CURDATE()
            ORDER BY a.check_in_time DESC
        """)
        records = cursor.fetchall()
        cursor.close()
        connection.close()

        return jsonify({'success': True, 'data': records})
    except Error as e:
        print(f"[ERROR] /api/attendance/today: {e}")
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500

@app.route('/api/recognize', methods=['POST'])
@login_required
def api_recognize():
    """API endpoint for face recognition from server camera"""
    # Check if model exists
    model_path = os.path.join('model', 'lbph_model.yml')
    if not os.path.exists(model_path):
        return jsonify({'success': False, 'message': 'Model belum di-training'}), 400

    global camera, recognizer

    # Load recognizer if not loaded
    if recognizer is None:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(model_path)

    # Initialize camera if not initialized
    if camera is None:
        camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        return jsonify({'success': False, 'message': 'Gagal membuka kamera'}), 500

    try:
        # Capture frame
        ret, frame = camera.read()
        if not ret:
            return jsonify({'success': False, 'message': 'Gagal membaca frame dari kamera'}), 500

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            return jsonify({'success': False, 'message': 'Tidak ada wajah terdeteksi'})

        # Get first face
        (x, y, w, h) = faces[0]
        face_roi = gray[y:y+h, x:x+w]

        # Recognize
        student_id, confidence = recognizer.predict(face_roi)

        # Check confidence threshold
        confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', 50))

        if confidence > confidence_threshold:
            return jsonify({'success': False, 'message': f'Wajah tidak dikenali (confidence: {confidence:.1f})'})

        # Get student info
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, nis, name FROM students WHERE id = %s AND is_active = 1", (student_id,))
        student = cursor.fetchone()

        if not student:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Siswa tidak ditemukan'})

        # Check if already attended today
        cursor.execute("""
            SELECT id FROM attendance
            WHERE student_id = %s AND attendance_date = CURDATE()
        """, (student_id,))

        if cursor.fetchone():
            cursor.close()
            connection.close()
            return jsonify({
                'success': False,
                'message': f"{student['name']} sudah absen hari ini",
                'student': student
            })

        # Record attendance
        late_after_str = os.getenv('LATE_AFTER', '08:00:00')
        late_after_time = datetime.strptime(late_after_str, '%H:%M:%S').time()
        current_time = datetime.now().time()
        status = 'Terlambat' if current_time > late_after_time else 'Hadir'

        cursor.execute("""
            INSERT INTO attendance (student_id, attendance_date, check_in_time, status, confidence)
            VALUES (%s, CURDATE(), %s, %s, %s)
        """, (student_id, current_time, status, confidence))
        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({
            'success': True,
            'message': f"Absensi berhasil - {status}",
            'student': student,
            'status': status,
            'confidence': float(confidence)
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/check_today_attendance', methods=['GET'])
@login_required
def api_check_today_attendance():
    """Check if user has attended today"""
    user = get_current_user()

    if not user.get('student_id'):
        return jsonify({'attended': False})

    connection = get_db_connection()
    if connection is None:
        return jsonify({'attended': False})

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT check_in_time, status
            FROM attendance
            WHERE student_id = %s AND attendance_date = CURDATE()
        """, (user['student_id'],))

        record = cursor.fetchone()
        cursor.close()
        connection.close()

        if record:
            return jsonify({
                'attended': True,
                'check_in_time': str(record['check_in_time']),
                'status': record['status']
            })
        else:
            return jsonify({'attended': False})

    except Exception as e:
        return jsonify({'attended': False})

@app.route('/register-new', methods=['GET', 'POST'])
def register_new():
    """Public registration page for new students"""
    if request.method == 'POST':
        nis = request.form.get('nis', '').strip()
        name = request.form.get('name', '').strip()
        class_name = request.form.get('class_name', '').strip()
        gender = request.form.get('gender', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not nis or not name or not gender or not password:
            flash('Semua field wajib diisi', 'danger')
            return redirect(url_for('register_new'))

        if password != confirm_password:
            flash('Password tidak cocok', 'danger')
            return redirect(url_for('register_new'))

        if len(password) < 6:
            flash('Password minimal 6 karakter', 'danger')
            return redirect(url_for('register_new'))

        connection = get_db_connection()
        if connection is None:
            flash('Koneksi database gagal', 'danger')
            return redirect(url_for('register_new'))

        try:
            cursor = connection.cursor()

            # Check if NIS already exists
            cursor.execute("SELECT id FROM students WHERE nis = %s", (nis,))
            if cursor.fetchone():
                flash('NIS sudah terdaftar', 'danger')
                return redirect(url_for('register_new'))

            # Create student
            cursor.execute("""
                INSERT INTO students (nis, name, class_name, gender, is_active)
                VALUES (%s, %s, %s, %s, 1)
            """, (nis, name, class_name, gender))
            student_id = cursor.lastrowid

            # Create user account
            from src.auth_web import hash_password
            hashed_pw = hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password, full_name, role, student_id, is_active)
                VALUES (%s, %s, %s, 'user', %s, 1)
            """, (nis, hashed_pw, name, student_id))

            connection.commit()
            cursor.close()
            connection.close()

            flash('Registrasi berhasil! Silakan login dengan NIS dan password Anda.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('register_new'))

    return render_template('register_new.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if is_authenticated():
        user = get_current_user()
        if user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Username dan password tidak boleh kosong', 'danger')
            return redirect(url_for('login'))

        success, message, user_data = authenticate_user(username, password)

        if success:
            login_user(user_data)
            flash(f'Selamat datang, {user_data["full_name"]}!', 'success')

            if user_data['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('user.dashboard'))
        else:
            flash(message, 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('Anda telah logout', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))
