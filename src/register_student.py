import cv2
import os
from datetime import datetime
from src.database import get_db_connection
from mysql.connector import Error

def register_student():
    """Register new employee and capture face samples"""
    print("=" * 50)
    print("REGISTRASI KARYAWAN")
    print("=" * 50)

    # Input employee data
    nip = input("Masukkan NIP: ").strip()
    if not nip:
        print("NIP tidak boleh kosong!")
        return

    name = input("Masukkan Nama: ").strip()
    if not name:
        print("Nama tidak boleh kosong!")
        return

    department = input("Masukkan Departemen/Divisi: ").strip()

    gender = input("Jenis Kelamin (L/P): ").strip().upper()
    while gender not in ['L', 'P']:
        print("Jenis kelamin harus L atau P!")
        gender = input("Jenis Kelamin (L/P): ").strip().upper()

    # Connect to database
    connection = get_db_connection()
    if connection is None:
        print("Gagal terhubung ke database!")
        return

    try:
        cursor = connection.cursor()

        # Check if NIP already exists
        cursor.execute("SELECT id FROM employees WHERE nip = %s", (nip,))
        if cursor.fetchone():
            print(f"NIP {nip} sudah terdaftar!")
            cursor.close()
            connection.close()
            return

        # Resolve department -> department_id (create if needed)
        department_id = None
        if department:
            cursor.execute("SELECT id FROM departments WHERE name = %s", (department,))
            row = cursor.fetchone()
            if row:
                department_id = row[0]
            else:
                cursor.execute("INSERT INTO departments (name) VALUES (%s)", (department,))
                department_id = cursor.lastrowid

        # Insert employee data
        insert_query = """
            INSERT INTO employees (nip, name, department_id, gender)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (nip, name, department_id, gender))
        connection.commit()
        employee_id = cursor.lastrowid

        print(f"\nData karyawan berhasil disimpan dengan ID: {employee_id}")
        print("\nMemulai pengambilan sampel wajah...")
        print("Instruksi:")
        print("- Hadapkan wajah ke kamera")
        print("- Pastikan pencahayaan cukup")
        print("- Gerakkan wajah sedikit (kiri, kanan, atas, bawah)")
        print("- Tekan 'q' untuk membatalkan")

        # Capture face samples
        samples_captured = capture_face_samples(employee_id, cursor, connection)

        if samples_captured > 0:
            print(f"\n{samples_captured} sampel wajah berhasil disimpan!")
            print("Silakan jalankan training model: python -m src.train_model")
        else:
            print("\nGagal mengambil sampel wajah!")
            # Delete employee data if no samples captured
            cursor.execute("DELETE FROM employees WHERE id = %s", (employee_id,))
            connection.commit()
            print("Data karyawan dihapus karena tidak ada sampel wajah.")

        cursor.close()
        connection.close()

    except Error as e:
        print(f"Error: {e}")
        if connection:
            connection.close()

def capture_face_samples(employee_id, cursor, connection):
    """Capture face samples using webcam"""
    # Load face cascade classifier
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Initialize webcam
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Error: Tidak dapat membuka kamera!")
        return 0

    # Create directory for employee samples
    dataset_path = os.path.join('dataset', str(employee_id))
    os.makedirs(dataset_path, exist_ok=True)

    sample_count = 0
    max_samples = int(os.getenv('SAMPLES_PER_PERSON', 30))

    print(f"\nMengambil {max_samples} sampel wajah...")

    while sample_count < max_samples:
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

        # Process detected faces
        for (x, y, w, h) in faces:
            # Draw rectangle around face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Save face sample
            sample_count += 1
            face_img = gray[y:y+h, x:x+w]
            face_img = cv2.resize(face_img, (150, 150))

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sample_{sample_count}_{timestamp}.jpg"
            filepath = os.path.join(dataset_path, filename)

            # Save image
            cv2.imwrite(filepath, face_img)

            # Save to database
            try:
                insert_query = """
                    INSERT INTO face_samples (employee_id, image_path)
                    VALUES (%s, %s)
                """
                cursor.execute(insert_query, (employee_id, filepath))
                connection.commit()
            except Error as e:
                print(f"Error saving sample to database: {e}")

            # Display progress
            cv2.putText(
                frame,
                f"Sampel: {sample_count}/{max_samples}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        # Display frame
        cv2.imshow('Registrasi Wajah - Tekan q untuk batal', frame)

        # Check for quit key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nPengambilan sampel dibatalkan!")
            break

    # Release resources
    camera.release()
    cv2.destroyAllWindows()

    return sample_count

if __name__ == "__main__":
    register_student()
