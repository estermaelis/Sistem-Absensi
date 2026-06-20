from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, Response, session, flash
import cv2
import os
import numpy as np
import time
from datetime import datetime, date
from dotenv import load_dotenv
from src.database import get_db_connection
from mysql.connector import Error
import base64
from io import BytesIO
from PIL import Image
from src.auth_web import authenticate_user, login_user, logout_user, is_authenticated, get_current_user, login_required, admin_required
from src.activity_log import log_activity

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Register blueprints
from routes_admin import admin_bp
from routes_admin_users import admin_users_bp
from routes_user import user_bp
from routes_departments import departments_bp

app.register_blueprint(admin_bp)
app.register_blueprint(admin_users_bp)
app.register_blueprint(user_bp)
app.register_blueprint(departments_bp)

# Global variables
camera = None
recognizer = None
latest_frame = None
import threading
frame_lock = threading.Lock()
capture_progress = {'phase': '', 'saved': 0, 'total': 0, 'running': False}
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')

@app.route('/')
def index():
    """Root - arahkan ke login, atau ke dashboard sesuai role jika sudah login"""
    if is_authenticated():
        user = get_current_user()
        if user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    return redirect(url_for('login'))

@app.route('/students')
def students():
    """List all employees"""
    connection = get_db_connection()
    if connection is None:
        return render_template('error.html', message="Database connection failed")

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

        return render_template('students.html', employees=employees_list)
    except Error as e:
        return render_template('error.html', message=f"Database error: {e}")

@app.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for employee registration"""
    data = request.json

    nip = data.get('nip', '').strip()
    name = data.get('name', '').strip()
    department_id = data.get('department_id') or None
    email = data.get('email', '').strip() or None
    gender = data.get('gender', '').strip().upper()

    if not nip or not name or not gender:
        return jsonify({'success': False, 'message': 'Data tidak lengkap'}), 400

    if gender not in ['L', 'P']:
        return jsonify({'success': False, 'message': 'Jenis kelamin harus L atau P'}), 400

    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor()

        # Check if NIP exists
        cursor.execute("SELECT id FROM employees WHERE nip = %s", (nip,))
        if cursor.fetchone():
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': f'NIP {nip} sudah terdaftar'}), 400

        # Insert employee
        insert_query = "INSERT INTO employees (nip, name, department_id, email, gender) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (nip, name, department_id, email, gender))
        connection.commit()
        employee_id = cursor.lastrowid

        cursor.close()
        connection.close()

        return jsonify({'success': True, 'message': 'Karyawan berhasil didaftarkan', 'employee_id': employee_id})

    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500

def generate_frames():
    """Generate video frames from camera"""
    global camera, latest_frame
    if camera is None:
        camera = cv2.VideoCapture(0)

    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            with frame_lock:
                latest_frame = frame.copy()
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
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/start_camera', methods=['POST'])
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
def api_stop_camera():
    """Stop camera"""
    global camera, latest_frame
    if camera is not None:
        camera.release()
        camera = None
    latest_frame = None
    return jsonify({'success': True, 'message': 'Kamera dimatikan'})

@app.route('/api/capture_samples', methods=['POST'])
def api_capture_samples():
    """API endpoint to capture all face samples automatically in one go.
    Captures faces across multiple phases: front, left/right, up/down.
    Returns progress per phase so frontend can show guided directions.
    """
    data = request.json
    employee_id = data.get('employee_id')

    if not employee_id:
        return jsonify({'success': False, 'message': 'ID Karyawan tidak ditemukan'}), 400

    global camera, latest_frame
    if camera is None:
        camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        return jsonify({'success': False, 'message': 'Gagal membuka kamera'}), 500

    connection = get_db_connection()
    if connection is None:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    global capture_progress
    capture_progress = {'phase': 'memulai', 'saved': 0, 'total': 0, 'running': True}

    try:
        # Create directory for employee
        dataset_path = os.path.join('dataset', str(employee_id))
        os.makedirs(dataset_path, exist_ok=True)

        cursor = connection.cursor()

        # Clear previous samples for this employee
        cursor.execute("SELECT image_path FROM face_samples WHERE employee_id = %s", (employee_id,))
        old_samples = cursor.fetchall()
        for (old_path,) in old_samples:
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass
        cursor.execute("DELETE FROM face_samples WHERE employee_id = %s", (employee_id,))
        connection.commit()

        total_saved = 0
        samples_per_phase = 10
        max_trials_per_phase = 60

        # Define phases
        phases = ['depan', 'kiri_kanan', 'atas_bawah']
        phase_results = {}

        for phase in phases:
            saved = 0
            trials = 0
            capture_progress = {'phase': phase, 'saved': total_saved, 'total': samples_per_phase * len(phases), 'running': True}

            while saved < samples_per_phase and trials < max_trials_per_phase:
                trials += 1
                frame = None
                with frame_lock:
                    if latest_frame is not None:
                        frame = latest_frame.copy()

                if frame is None:
                    ret, frame = camera.read()
                    if not ret:
                        time.sleep(0.05)
                        continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                face_img = None

                try:
                    if phase == 'depan':
                        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))
                        if len(faces) > 0:
                            (x, y, w, h) = faces[0]
                            face_img = gray[y:y+h, x:x+w]
                    elif phase == 'kiri_kanan':
                        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))
                        if len(faces) > 0:
                            (x, y, w, h) = faces[0]
                            face_img = gray[y:y+h, x:x+w]
                        else:
                            profiles = profile_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))
                            if len(profiles) > 0:
                                (x, y, w, h) = profiles[0]
                                face_img = gray[y:y+h, x:x+w]
                            else:
                                flipped_gray = cv2.flip(gray, 1)
                                left_profiles = profile_cascade.detectMultiScale(flipped_gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))
                                if len(left_profiles) > 0:
                                    (x, y, w, h) = left_profiles[0]
                                    face_img = flipped_gray[y:y+h, x:x+w]
                    elif phase == 'atas_bawah':
                        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=4, minSize=(30, 30))
                        if len(faces) > 0:
                            (x, y, w, h) = faces[0]
                            face_img = gray[y:y+h, x:x+w]
                except cv2.error:
                    face_img = None

                if face_img is not None:
                    face_img = cv2.resize(face_img, (150, 150))

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    filename = f"sample_{phase}_{saved+1}_{timestamp}.jpg"
                    filepath = os.path.join(dataset_path, filename)
                    cv2.imwrite(filepath, face_img)

                    insert_query = "INSERT INTO face_samples (employee_id, image_path) VALUES (%s, %s)"
                    cursor.execute(insert_query, (employee_id, filepath))
                    saved += 1
                    total_saved += 1
                    capture_progress['saved'] = total_saved

                    time.sleep(0.15)
                else:
                    time.sleep(0.05)

            phase_results[phase] = saved

        connection.commit()
        cursor.close()
        connection.close()

        capture_progress = {'phase': 'selesai', 'saved': total_saved, 'total': samples_per_phase * len(phases), 'running': False}

        if total_saved >= (samples_per_phase * len(phases)):
            return jsonify({
                'success': True,
                'message': f'Registrasi wajah sukses! {total_saved} foto dari semua arah berhasil disimpan.',
                'total': total_saved,
                'phases': phase_results
            })
        else:
            return jsonify({
                'success': total_saved >= 15,
                'message': f'{total_saved} foto berhasil disimpan (depan: {phase_results.get("depan",0)}, samping: {phase_results.get("kiri_kanan",0)}, atas/bawah: {phase_results.get("atas_bawah",0)}). Pastikan wajah terlihat jelas.',
                'total': total_saved,
                'phases': phase_results
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        capture_progress = {'phase': 'error', 'saved': 0, 'total': 0, 'running': False, 'error': str(e)}
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/capture_status', methods=['GET'])
def api_capture_status():
    """API endpoint to check real-time face capture progress"""
    global capture_progress
    return jsonify(capture_progress)

@app.route('/train')
def train():
    """Training page"""
    return render_template('train.html')

@app.route('/api/train', methods=['POST'])
def api_train():
    """API endpoint to train model"""
    from src.train_model_enhanced import train_model_enhanced

    global recognizer
    try:
        train_model_enhanced()
        # Invalidate cached model so the next recognition reloads the fresh one
        recognizer = None
        if is_authenticated():
            u = get_current_user()
            log_activity(u['id'], u['username'], 'training_model', 'Model wajah dilatih ulang')
        return jsonify({'success': True, 'message': 'Model berhasil dilatih'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/attendance')
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
            SELECT e.nip, e.name,
                   TIME_FORMAT(a.check_in_time, '%H:%i:%s') as check_in_time,
                   TIME_FORMAT(a.check_out_time, '%H:%i:%s') as check_out_time,
                   a.status
            FROM attendance a
            INNER JOIN employees e ON a.employee_id = e.id
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
def api_recognize():
    """API endpoint for face recognition from server camera"""
    # Check if model exists
    model_path = os.path.join('model', 'lbph_model.yml')
    if not os.path.exists(model_path):
        return jsonify({'success': False, 'message': 'Model belum di-training'}), 400

    global camera, recognizer, latest_frame

    # Load recognizer if not loaded
    if recognizer is None:
        recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8
        )
        recognizer.read(model_path)

    # Initialize camera if not initialized
    if camera is None:
        camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        return jsonify({'success': False, 'message': 'Gagal membuka kamera'}), 500

    try:
        # Capture frame
        frame = None
        with frame_lock:
            if latest_frame is not None:
                frame = latest_frame.copy()

        if frame is None:
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

        # Standardize size to match training data size
        face_roi = cv2.resize(face_roi, (150, 150))

        # Apply histogram equalization (same as training)
        face_roi = cv2.equalizeHist(face_roi)

        # Recognize
        employee_id, confidence = recognizer.predict(face_roi)

        # Check confidence threshold
        confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', 70))

        if confidence > confidence_threshold:
            return jsonify({'success': False, 'message': f'Wajah tidak dikenali (confidence: {confidence:.1f})'})

        # Get employee info
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, nip, name FROM employees WHERE id = %s AND is_active = 1", (employee_id,))
        employee = cursor.fetchone()

        if not employee:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Karyawan tidak ditemukan'})

        # Get today's attendance record (if any)
        cursor.execute("""
            SELECT id, check_in_time, check_out_time
            FROM attendance
            WHERE employee_id = %s AND attendance_date = CURDATE()
        """, (employee_id,))
        today_record = cursor.fetchone()

        current_time = datetime.now().time()

        if today_record is None:
            # First scan today -> check-in
            late_after_str = os.getenv('LATE_AFTER', '08:00:00')
            late_after_time = datetime.strptime(late_after_str, '%H:%M:%S').time()
            status = 'Terlambat' if current_time > late_after_time else 'Hadir'

            cursor.execute("""
                INSERT INTO attendance (employee_id, attendance_date, check_in_time, status, confidence)
                VALUES (%s, CURDATE(), %s, %s, %s)
            """, (employee_id, current_time, status, confidence))
            connection.commit()
            cursor.close()
            connection.close()

            return jsonify({
                'success': True,
                'message': f"Absen masuk berhasil - {status}",
                'employee': employee,
                'status': status,
                'type': 'check_in',
                'check_in_time': current_time.strftime('%H:%M:%S'),
                'confidence': float(confidence)
            })

        elif today_record['check_out_time'] is None:
            # Already checked in, no check-out yet -> check-out
            cursor.execute("""
                UPDATE attendance SET check_out_time = %s
                WHERE id = %s
            """, (current_time, today_record['id']))
            connection.commit()
            cursor.close()
            connection.close()

            return jsonify({
                'success': True,
                'message': "Absen pulang berhasil",
                'employee': employee,
                'status': 'Pulang',
                'type': 'check_out',
                'check_out_time': current_time.strftime('%H:%M:%S'),
                'confidence': float(confidence)
            })

        else:
            # Both check-in and check-out done
            cursor.close()
            connection.close()
            return jsonify({
                'success': False,
                'message': f"{employee['name']} sudah absen masuk & pulang hari ini",
                'employee': employee
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/check_today_attendance', methods=['GET'])
@login_required
def api_check_today_attendance():
    """Check if user has attended today"""
    user = get_current_user()

    if not user.get('employee_id'):
        return jsonify({'attended': False})

    connection = get_db_connection()
    if connection is None:
        return jsonify({'attended': False})

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT check_in_time, check_out_time, status
            FROM attendance
            WHERE employee_id = %s AND attendance_date = CURDATE()
        """, (user['employee_id'],))

        record = cursor.fetchone()
        cursor.close()
        connection.close()

        if record:
            return jsonify({
                'attended': True,
                'check_in_time': str(record['check_in_time']),
                'check_out_time': str(record['check_out_time']) if record['check_out_time'] else None,
                'status': record['status']
            })
        else:
            return jsonify({'attended': False})

    except Exception as e:
        return jsonify({'attended': False})

@app.route('/register-new', methods=['GET', 'POST'])
def register_new():
    """Public registration page for new employees"""
    if request.method == 'POST':
        nip = request.form.get('nip', '').strip()
        name = request.form.get('name', '').strip()
        department_id = request.form.get('department_id') or None
        email = request.form.get('email', '').strip() or None
        gender = request.form.get('gender', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not nip or not name or not gender or not password:
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

            # Check if NIP already exists
            cursor.execute("SELECT id FROM employees WHERE nip = %s", (nip,))
            if cursor.fetchone():
                flash('NIP sudah terdaftar', 'danger')
                return redirect(url_for('register_new'))

            # Create employee
            cursor.execute("""
                INSERT INTO employees (nip, name, department_id, email, gender, is_active)
                VALUES (%s, %s, %s, %s, %s, 1)
            """, (nip, name, department_id, email, gender))
            employee_id = cursor.lastrowid

            # Create user account
            from src.auth_web import hash_password
            hashed_pw = hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password, full_name, role, employee_id, is_active)
                VALUES (%s, %s, %s, 'user', %s, 1)
            """, (nip, hashed_pw, name, employee_id))

            connection.commit()
            cursor.close()
            connection.close()

            flash('Registrasi berhasil! Silakan login dengan NIP dan password Anda.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('register_new'))

    # GET: load departments for the dropdown
    departments = []
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM departments ORDER BY name")
            departments = cursor.fetchall()
            cursor.close()
            connection.close()
        except Error:
            pass

    return render_template('register_new.html', departments=departments)

@app.route('/register')
def register():
    """Public face registration page: add employee then capture face samples"""
    departments = []
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM departments ORDER BY name")
            departments = cursor.fetchall()
            cursor.close()
            connection.close()
        except Error:
            pass
    return render_template('register_face.html', departments=departments)

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
            log_activity(user_data['id'], user_data['username'], 'login', f"Login sebagai {user_data['role']}")
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
    u = get_current_user()
    if u:
        log_activity(u['id'], u['username'], 'logout', None)
    logout_user()
    flash('Anda telah logout', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))
