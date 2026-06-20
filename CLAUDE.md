# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Web-based face recognition attendance system (Sistem Absensi) built with Flask, OpenCV (LBPH algorithm), and MySQL. UI text and user-facing messages are in Indonesian — match this language when editing templates or flash/JSON messages.

## Commands

Run from the project root. On Windows, use the venv interpreter directly:

```powershell
# Run the app (HTTPS on port 5000, requires cert.pem + key.pem)
.\.venv\Scripts\python.exe app.py

# Train the face recognition model (CLI)
.\.venv\Scripts\python.exe -m src.train_model            # basic
.\.venv\Scripts\python.exe -m src.train_model_enhanced   # with data augmentation

# Initialize database + tables
.\.venv\Scripts\python.exe -m src.database

# Install dependencies
pip install -r requirements.txt
```

Database setup via SQL: `mysql -u root -p < database/complete_database_setup.sql`

There is no test suite or linter configured.

## Configuration

Copy `.env.example` to `.env`. Key vars consumed at runtime:
- `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` — MySQL connection (see `src/database.py`)
- `CONFIDENCE_THRESHOLD` — LBPH distance cutoff; **lower = stricter match** (a face is accepted when `confidence <= threshold`). `.env.example` ships 50.
- `LATE_AFTER` — time after which attendance is marked `Terlambat` instead of `Hadir`

The app runs with `ssl_context=('cert.pem', 'key.pem')` hardcoded in `app.py` — both files must exist in the root or startup fails. See README "Generate SSL Certificate" for the openssl one-liner.

## Architecture

**Flask app with blueprints.** `app.py` is the entrypoint and holds public/unauthenticated routes (index, face capture, recognition, registration, login). Three blueprints are registered, all using role decorators from `src/auth_web.py`:
- `routes_admin.py` (`/admin`) — student CRUD
- `routes_admin_users.py` (`/admin`) — user account CRUD + reports/statistics
- `routes_user.py` (`/user`) — per-student dashboard, history, profile

**Auth & roles.** `src/auth_web.py` is the single source for authentication. Passwords are bcrypt-hashed. Session-based; two roles (`admin`, `user`). Use the decorators `@login_required`, `@admin_required`, `@user_required` to protect routes. A `user` row links to a `students` row via `student_id`.

**Server-side camera (critical).** Face capture and recognition use the camera attached to the **server** (`cv2.VideoCapture(0)`), NOT the browser's webcam. The camera, recognizer model, and latest frame are module-level globals in `app.py` guarded by `frame_lock`. `/video_feed` streams MJPEG. This means the system only works when running on a machine with a physical camera, and only one client's capture makes sense at a time.

**Face recognition pipeline.**
1. Capture: `/api/capture_samples` records samples in 3 phases (`depan`, `kiri_kanan`, `atas_bawah`) into `dataset/<student_id>/`, 10 each, writing rows to `face_samples`. Progress is polled via `/api/capture_status` (global `capture_progress` dict).
2. Train: builds an LBPH model (`radius=1, neighbors=8, grid_x=8, grid_y=8`) from all active students' samples, saves to `model/lbph_model.yml`. The enhanced variant (`train_model_enhanced.py`) augments each image (rotation, brightness, blur, flip ~7x). Preprocessing for both training and recognition: grayscale → resize 150x150 → `equalizeHist`. **Any change to preprocessing must be mirrored in both the training module and `app.py`'s `/api/recognize`, or recognition silently degrades.**
3. Recognize: `/api/recognize` predicts a `student_id`, applies the confidence threshold, then records attendance with a duplicate-per-day guard.

**Two training modules exist.** `app.py`'s `/api/train` route calls `train_model_enhanced()`. The README and CLI docs reference `src.train_model` (basic). Both write to the same `model/lbph_model.yml`. The cached global `recognizer` in `app.py` is set to `None` after training to force a reload.

**Database layer.** `src/database.py` exposes `get_db_connection()` (returns a fresh connection with the DB selected) and table-creation helpers. There is no ORM and no connection pool — every route opens and closes its own connection and runs raw parameterized SQL. Tables: `students`, `face_samples` (FK → students, CASCADE), `attendance` (unique per student+date), `users` (auth, optional FK → students).

**Standalone CLI scripts.** `src/attendance.py` and `src/register_student.py` are OpenCV desktop (cv2.imshow) versions that predate the web UI. They are not imported by the web app.

## Conventions

- Raw SQL with `%s` placeholders everywhere — never string-format user input into queries.
- Auto-generated dirs (`model/`, `dataset/`, `exports/`, `static/uploads/`) are created on demand with `os.makedirs(..., exist_ok=True)`.
- `app.config['SECRET_KEY']` is currently hardcoded in `app.py` — move to env before any non-local deployment.
