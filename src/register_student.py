import cv2
import os
from datetime import datetime
from src.database import get_db_connection
from mysql.connector import Error

def register_student():
    """Register new student and capture face samples"""
    print("=" * 50)
    print("REGISTRASI SISWA/KARYAWAN")
    print("=" * 50)

    # Input student data
    nis = input("Masukkan NIS: ").strip()
    if not nis:
        print("NIS tidak boleh kosong!")
        return

    name = input("Masukkan Nama: ").strip()
    if not name:
        print("Nama tidak boleh kosong!")
        return

    class_name = input("Masukkan Kelas/Divisi: ").strip()

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

        # Check if NIS already exists
        cursor.execute("SELECT id FROM students WHERE nis = %s", (nis,))
        if cursor.fetchone():
            print(f"NIS {nis} sudah terdaftar!")
            cursor.close()
            connection.close()
            return

        # Insert student data
        insert_query = """
            INSERT INTO students (nis, name, class_name, gender)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (nis, name, class_name, gender))
        connection.commit()
        student_id = cursor.lastrowid

        print(f"\nData siswa berhasil disimpan dengan ID: {student_id}")
        print("\nMemulai pengambilan sampel wajah...")
        print("Instruksi:")
        print("- Hadapkan wajah ke kamera")
        print("- Pastikan pencahayaan cukup")
        print("- Gerakkan wajah sedikit (kiri, kanan, atas, bawah)")
        print("- Tekan 'q' untuk membatalkan")

        # Capture face samples
        samples_captured = capture_face_samples(student_id, cursor, connection)

        if samples_captured > 0:
            print(f"\n{samples_captured} sampel wajah berhasil disimpan!")
            print("Silakan jalankan training model: python -m src.train_model")
        else:
            print("\nGagal mengambil sampel wajah!")
            # Delete student data if no samples captured
            cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
            connection.commit()
            print("Data siswa dihapus karena tidak ada sampel wajah.")

        cursor.close()
        connection.close()

    except Error as e:
        print(f"Error: {e}")
        if connection:
            connection.close()

def capture_face_samples(student_id, cursor, connection):
    """Capture face samples using webcam"""
    # Load face cascade classifier
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Initialize webcam
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Error: Tidak dapat membuka kamera!")
        return 0

    # Create directory for student samples
    dataset_path = os.path.join('dataset', str(student_id))
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

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sample_{sample_count}_{timestamp}.jpg"
            filepath = os.path.join(dataset_path, filename)

            # Save image
            cv2.imwrite(filepath, face_img)

            # Save to database
            try:
                insert_query = """
                    INSERT INTO face_samples (student_id, image_path)
                    VALUES (%s, %s)
                """
                cursor.execute(insert_query, (student_id, filepath))
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
