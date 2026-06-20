import cv2
import os
import numpy as np
from src.database import get_db_connection
from mysql.connector import Error

def augment_image(img):
    """Apply data augmentation to increase training samples"""
    augmented = []

    # Original
    augmented.append(img)

    # Slight rotation variations
    rows, cols = img.shape
    for angle in [-5, 5]:
        M = cv2.getRotationMatrix2D((cols/2, rows/2), angle, 1)
        rotated = cv2.warpAffine(img, M, (cols, rows))
        augmented.append(rotated)

    # Brightness variations
    for beta in [-20, 20]:
        bright = cv2.convertScaleAbs(img, alpha=1.0, beta=beta)
        augmented.append(bright)

    # Slight blur
    blurred = cv2.GaussianBlur(img, (3, 3), 0)
    augmented.append(blurred)

    # Horizontal flip (for non-profile faces)
    flipped = cv2.flip(img, 1)
    augmented.append(flipped)

    return augmented

def train_model_enhanced():
    """Train LBPH face recognition model with data augmentation"""
    print("=" * 50)
    print("ENHANCED TRAINING - DENGAN AUGMENTASI DATA")
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
            SELECT fs.employee_id, fs.image_path
            FROM face_samples fs
            INNER JOIN employees e ON fs.employee_id = e.id
            WHERE e.is_active = 1
            ORDER BY fs.employee_id
        """)

        samples = cursor.fetchall()
        cursor.close()
        connection.close()

        if not samples:
            print("Tidak ada sampel wajah yang ditemukan!")
            return

        print(f"Ditemukan {len(samples)} sampel wajah dari database.")
        print("Memuat gambar dengan augmentasi...")

        # Prepare training data
        faces = []
        labels = []
        loaded_count = 0
        augmented_count = 0

        for employee_id, image_path in samples:
            # Check if file exists
            if not os.path.exists(image_path):
                print(f"Warning: File tidak ditemukan: {image_path}")
                continue

            # Load image
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

            if img is None:
                print(f"Warning: Gagal membaca gambar: {image_path}")
                continue

            # Standardize size to 150x150
            img = cv2.resize(img, (150, 150))

            # Apply histogram equalization
            img = cv2.equalizeHist(img)

            # Apply augmentation
            augmented_images = augment_image(img)

            for aug_img in augmented_images:
                faces.append(aug_img)
                labels.append(employee_id)
                augmented_count += 1

            loaded_count += 1

        if loaded_count == 0:
            print("Tidak ada gambar yang berhasil dimuat!")
            return

        print(f"Berhasil memuat {loaded_count} gambar asli.")
        print(f"Total sampel setelah augmentasi: {augmented_count}")
        print("Memulai training model dengan parameter optimal...")

        # Create LBPH face recognizer with optimized parameters
        recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8
        )

        # Train the model
        recognizer.train(faces, np.array(labels))

        # Save the model
        model_path = os.path.join('model', 'lbph_model.yml')
        os.makedirs('model', exist_ok=True)
        recognizer.save(model_path)

        print(f"\nModel berhasil disimpan di: {model_path}")
        print("Enhanced training selesai!")
        print(f"Rasio augmentasi: {augmented_count / loaded_count:.1f}x")

    except Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    train_model_enhanced()
