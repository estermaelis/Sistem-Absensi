import csv
import os
from datetime import datetime
from src.database import get_db_connection
from mysql.connector import Error

def export_report():
    """Export attendance report to CSV"""
    print("=" * 50)
    print("EXPORT LAPORAN ABSENSI")
    print("=" * 50)

    # Connect to database
    connection = get_db_connection()
    if connection is None:
        print("Gagal terhubung ke database!")
        return

    try:
        # Get date range from user
        print("\nMasukkan rentang tanggal (kosongkan untuk semua data)")
        start_date = input("Tanggal awal (YYYY-MM-DD): ").strip()
        end_date = input("Tanggal akhir (YYYY-MM-DD): ").strip()

        cursor = connection.cursor(dictionary=True)

        # Build query based on date range
        if start_date and end_date:
            query = """
                SELECT
                    s.nis,
                    s.name,
                    s.class_name,
                    s.gender,
                    a.attendance_date,
                    a.check_in_time,
                    a.status,
                    a.confidence
                FROM attendance a
                INNER JOIN students s ON a.student_id = s.id
                WHERE a.attendance_date BETWEEN %s AND %s
                ORDER BY a.attendance_date DESC, a.check_in_time ASC
            """
            cursor.execute(query, (start_date, end_date))
            date_suffix = f"{start_date}_to_{end_date}"
        elif start_date:
            query = """
                SELECT
                    s.nis,
                    s.name,
                    s.class_name,
                    s.gender,
                    a.attendance_date,
                    a.check_in_time,
                    a.status,
                    a.confidence
                FROM attendance a
                INNER JOIN students s ON a.student_id = s.id
                WHERE a.attendance_date >= %s
                ORDER BY a.attendance_date DESC, a.check_in_time ASC
            """
            cursor.execute(query, (start_date,))
            date_suffix = f"from_{start_date}"
        else:
            query = """
                SELECT
                    s.nis,
                    s.name,
                    s.class_name,
                    s.gender,
                    a.attendance_date,
                    a.check_in_time,
                    a.status,
                    a.confidence
                FROM attendance a
                INNER JOIN students s ON a.student_id = s.id
                ORDER BY a.attendance_date DESC, a.check_in_time ASC
            """
            cursor.execute(query)
            date_suffix = "all"

        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        if not rows:
            print("\nTidak ada data absensi yang ditemukan!")
            return

        print(f"\nDitemukan {len(rows)} record absensi.")

        # Create exports directory
        os.makedirs('exports', exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"laporan_absensi_{date_suffix}_{timestamp}.csv"
        filepath = os.path.join('exports', filename)

        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'NIS',
                'Nama',
                'Kelas',
                'Jenis Kelamin',
                'Tanggal',
                'Jam Masuk',
                'Status',
                'Confidence'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header
            writer.writeheader()

            # Write data
            for row in rows:
                writer.writerow({
                    'NIS': row['nis'],
                    'Nama': row['name'],
                    'Kelas': row['class_name'] or '',
                    'Jenis Kelamin': 'Laki-laki' if row['gender'] == 'L' else 'Perempuan',
                    'Tanggal': row['attendance_date'].strftime('%Y-%m-%d'),
                    'Jam Masuk': str(row['check_in_time']),
                    'Status': row['status'],
                    'Confidence': f"{row['confidence']:.2f}" if row['confidence'] else ''
                })

        print(f"\nLaporan berhasil diekspor ke: {filepath}")
        print(f"Total record: {len(rows)}")

    except Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    export_report()
