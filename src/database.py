import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'attendance_db')
}

def get_connection():
    """Create and return database connection"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def get_db_connection():
    """Create and return database connection with database selected"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database']
        )
        return connection
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def create_database():
    """Create database if not exists"""
    connection = get_connection()
    if connection is None:
        return False

    try:
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        print(f"Database '{DB_CONFIG['database']}' created successfully or already exists.")
        cursor.close()
        connection.close()
        return True
    except Error as e:
        print(f"Error creating database: {e}")
        return False

def create_tables():
    """Create all required tables"""
    connection = get_db_connection()
    if connection is None:
        return False

    try:
        cursor = connection.cursor()

        # Create students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nis VARCHAR(30) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                class_name VARCHAR(50),
                gender ENUM('L', 'P') NOT NULL,
                is_active TINYINT(1) DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        print("Table 'students' created successfully.")

        # Create face_samples table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_samples (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                image_path VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
        """)
        print("Table 'face_samples' created successfully.")

        # Create attendance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                attendance_date DATE NOT NULL,
                check_in_time TIME NOT NULL,
                status ENUM('Hadir', 'Terlambat') NOT NULL,
                confidence DECIMAL(8,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE KEY unique_attendance (student_id, attendance_date)
            )
        """)
        print("Table 'attendance' created successfully.")

        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        print(f"Error creating tables: {e}")
        return False

def initialize_database():
    """Initialize database and tables"""
    print("Initializing database...")
    if create_database():
        if create_tables():
            print("\nDatabase initialization completed successfully!")
            return True
    print("\nDatabase initialization failed!")
    return False

if __name__ == "__main__":
    initialize_database()
