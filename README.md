# EduTrack — Student Attendance & Academic Management System

A clean full-stack role-based academic management platform for Students, Faculty, and Administrators.

## Stack
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: HTML5 + CSS3 + Vanilla JavaScript
- Authentication: role-based token sessions
- Reports: CSV export
- UI: responsive dashboard, charts, modals, tables, notifications

## Roles
- Student: personal attendance, calendar, calculator, prediction, leave, courses, assignments, grades, timetable, announcements, notifications, profile, AI assistant.
- Faculty: class dashboard, students, attendance, QR sessions, corrections, analytics, at-risk students, leave approval, assignments, grades, announcements, reports.
- Admin: institution dashboard, student/faculty/department/course/section/timetable management, analytics, leave, announcements, permissions, audit logs, reports, settings.

## Run

> The project uses Python's built-in PBKDF2-SHA256 password hashing, so it does not depend on Passlib/bcrypt. This avoids the bcrypt compatibility error that can occur with Python 3.13.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

Open http://127.0.0.1:8000

## Demo accounts
- Student: student@edutrack.local / student123
- Faculty: faculty@edutrack.local / faculty123
- Admin: admin@edutrack.local / admin123

The application seeds demo data automatically on first start.

## Project structure

```text
edutrack_fullstack/
├── backend/
│   ├── __init__.py
│   └── app.py
├── frontend/
│   ├── main.html
│   ├── styles.css
│   └── app.js
├── requirements.txt
└── README.md
```


## If you previously started the broken version

From the project directory, remove the old development database once:

```bash
rm -f edutrack.db
```

Then recreate the environment:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```
