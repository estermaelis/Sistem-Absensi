import cv2
import os
import numpy as np
from src.database import get_db_connection
from mysql.connector import Error

def train_model():
    """Train LBPH face recognition model"""
    print("=" * 50)
    print("TRAINING MODEL FACE RECOGNITION")
    print("=" * 50)

    # Connect to database
    connection = get_db_connection()
    if connection is None:
        print("Gagal terhubung ke database!")
        return

    try:
        cursor = connection.cursor()

        # Get all face samples from database
        cursor.execute("""
            SELECT fs.student_id, fs.image_path
            FROM face_samples fs
            INNER JOIN students s ON fs.student_id = s.id
            WHERE s.is_active = 1
            ORDER BY fs.student_id
        """)

        samples = cursor.fetchall()
        cursor.close()
        connection.close()

        if not samples:
            print("Tidak ada sampel wajah yang ditemukan!")
            print("Silakan registrasi siswa terlebih dahulu: python -m src.register_student")
            return

        print(f"Ditemukan {len(samples)} sampel wajah dari database.")
        print("Memuat gambar...")

        # Prepare training data
        faces = []
        labels = []
        loaded_count = 0

        for student_id, image_path in samples:
            # Check if file exists
            if not os.path.exists(image_path):
                print(f"Warning: File tidak ditemukan: {image_path}")
                continue

            # Load image
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

            if img is None:
                print(f"Warning: Gagal membaca gambar: {image_path}")
                continue

            faces.append(img)
            labels.append(student_id)
            loaded_count += 1

        if loaded_count == 0:
            print("Tidak ada gambar yang berhasil dimuat!")
            return

        print(f"Berhasil memuat {loaded_count} gambar.")
        print("Memulai training model...")

        # Create LBPH face recognizer
        recognizer = cv2.face.LBPHFaceRecognizer_create()

        # Train the model
        recognizer.train(faces, np.array(labels))

        # Save the model
        model_path = os.path.join('model', 'lbph_model.yml')
        os.makedirs('model', exist_ok=True)
        recognizer.save(model_path)

        print(f"\nModel berhasil disimpan di: {model_path}")
        print("Training selesai!")
        print("\nAnda sekarang dapat menjalankan absensi: python -m src.attendance")

    except Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    train_model()
