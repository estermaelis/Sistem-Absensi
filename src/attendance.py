import cv2
import os
from datetime import datetime, date, time
from dotenv import load_dotenv
from src.database import get_db_connection
from mysql.connector import Error

# Load environment variables
load_dotenv()

def run_attendance():
    """Run real-time face recognition attendance system"""
    print("=" * 50)
    print("SISTEM ABSENSI FACE RECOGNITION")
    print("=" * 50)

    # Check if model exists
    model_path = os.path.join('model', 'lbph_model.yml')
    if not os.path.exists(model_path):
        print("Model tidak ditemukan!")
        print("Silakan jalankan training terlebih dahulu: python -m src.train_model")
        return

    # Load face cascade and recognizer
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=1,
        neighbors=8,
        grid_x=8,
        grid_y=8
    )
    recognizer.read(model_path)

    # Get configuration
    confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', 50))
    late_after_str = os.getenv('LATE_AFTER', '08:00:00')
    late_after_time = datetime.strptime(late_after_str, '%H:%M:%S').time()

    # Connect to database
    connection = get_db_connection()
    if connection is None:
        print("Gagal terhubung ke database!")
        return

    # Load employee data
    employees = load_students(connection)
    if not employees:
        print("Tidak ada data karyawan aktif!")
        connection.close()
        return

    print(f"Model dimuat. Threshold confidence: {confidence_threshold}")
    print(f"Batas waktu terlambat: {late_after_str}")
    print(f"Total karyawan aktif: {len(employees)}")
    print("\nTekan 'q' untuk keluar\n")

    # Initialize webcam
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Error: Tidak dapat membuka kamera!")
        connection.close()
        return

    # Track recently recognized faces to avoid duplicate entries
    recent_recognitions = {}
    recognition_cooldown = 5  # seconds

    while True:
        ret, frame = camera.read()
        if not ret:
            print("Error: Gagal membaca frame dari kamera!")
            break

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.3,
            minNeighbors=5,
            minSize=(30, 30)
        )

        # Process each detected face
        for (x, y, w, h) in faces:
            # Extract face region
            face_roi = gray[y:y+h, x:x+w]

            # Resize to match training data size
            face_roi = cv2.resize(face_roi, (150, 150))

            # Apply histogram equalization (same as training)
            face_roi = cv2.equalizeHist(face_roi)

            # Recognize face
            employee_id, confidence = recognizer.predict(face_roi)

            # Check if confidence is within threshold
            if confidence <= confidence_threshold:
                # Get employee info
                employee_info = employees.get(employee_id)

                if employee_info:
                    name = employee_info['name']
                    nip = employee_info['nip']

                    # Check cooldown
                    current_time = datetime.now()
                    if employee_id in recent_recognitions:
                        last_recognition = recent_recognitions[employee_id]
                        time_diff = (current_time - last_recognition).total_seconds()
                        if time_diff < recognition_cooldown:
                            # Still in cooldown, skip
                            label = f"{name} (Cooldown)"
                            color = (0, 165, 255)  # Orange
                            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                            continue

                    # Record attendance
                    success, message = record_attendance(
                        connection,
                        employee_id,
                        confidence,
                        late_after_time
                    )

                    if success:
                        recent_recognitions[employee_id] = current_time
                        print(f"[{current_time.strftime('%H:%M:%S')}] {message}")
                        label = f"{name} - {message}"
                        color = (0, 255, 0)  # Green
                    else:
                        label = f"{name} - {message}"
                        color = (0, 0, 255)  # Red

                    # Draw rectangle and label
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                    cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    cv2.putText(frame, f"Conf: {confidence:.1f}", (x, y+h+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                else:
                    # Employee ID not found in database
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    cv2.putText(frame, "Unknown ID", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            else:
                # Confidence too low
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, "Unknown", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(frame, f"Conf: {confidence:.1f}", (x, y+h+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Display frame
        cv2.imshow('Sistem Absensi - Tekan q untuk keluar', frame)

        # Check for quit key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    camera.release()
    cv2.destroyAllWindows()
    connection.close()
    print("\nSistem absensi ditutup.")

def load_students(connection):
    """Load active employees from database"""
    employees = {}
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.id, e.nip, e.name, d.name AS department_name, e.gender
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE e.is_active = 1
        """)
        rows = cursor.fetchall()
        for row in rows:
            employees[row['id']] = row
        cursor.close()
    except Error as e:
        print(f"Error loading employees: {e}")
    return employees

def record_attendance(connection, employee_id, confidence, late_after_time):
    """Record attendance to database"""
    try:
        cursor = connection.cursor()

        # Get current date and time
        today = date.today()
        now = datetime.now()
        current_time = now.time()

        # Check if already attended today
        cursor.execute("""
            SELECT id FROM attendance
            WHERE employee_id = %s AND attendance_date = %s
        """, (employee_id, today))

        if cursor.fetchone():
            cursor.close()
            return False, "Sudah absen hari ini"

        # Determine status
        status = 'Terlambat' if current_time > late_after_time else 'Hadir'

        # Insert attendance record
        insert_query = """
            INSERT INTO attendance (employee_id, attendance_date, check_in_time, status, confidence)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (employee_id, today, current_time, status, confidence))
        connection.commit()
        cursor.close()

        return True, f"Absensi berhasil - {status}"

    except Error as e:
        print(f"Error recording attendance: {e}")
        return False, "Error sistem"

if __name__ == "__main__":
    run_attendance()
