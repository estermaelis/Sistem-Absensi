"""
Activity logging helper. Records system activity to the activity_logs table.
Fail-silent: logging must never break the action it accompanies.
"""
from src.database import get_db_connection


def log_activity(user_id, username, action, detail=None):
    """Record an activity log entry. Never raises."""
    try:
        connection = get_db_connection()
        if connection is None:
            return
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO activity_logs (user_id, username, action, detail) VALUES (%s, %s, %s, %s)",
            (user_id, username, action, detail)
        )
        connection.commit()
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"[WARN] log_activity gagal: {e}")
