# EduPulse — Smart Education Monitoring & Analytics Platform

A deploy-ready academic analytics prototype inspired by the supplied Alliance.ai and AUERP screenshots. It seeds 60 fictional students, six separate teacher accounts, six courses per student, course and attendance views, assessment activity, teacher alerts, and a transparent early-warning scoring baseline. All teacher accounts can browse the full student directory and cohort-wide analytics.

## Demo accounts

### Teacher accounts (all use password `Teacher@123`)

- `teacher@demo.edu` — Dr. Meera Sharma
- `arjun@demo.edu` — Prof. Arjun Menon
- `priya@demo.edu` — Dr. Priya Iyer
- `rahul@demo.edu` — Prof. Rahul Verma
- `kavya@demo.edu` — Dr. Kavya Nair
- `aditya@demo.edu` — Prof. Aditya Rao

### Student accounts

- `aarav@demo.edu` / `Student@123` (featured demo account)
- `diya@demo.edu`, `ishaan@demo.edu`, `ananya@demo.edu`, `kabir@demo.edu`, `sara@demo.edu` / `Student@123`
- Additional fictional accounts: `student07@demo.edu` through `student60@demo.edu`, all with password `Student@123`.

The database seeding is idempotent: it adds missing demo accounts and records without duplicating existing ones. All records are fictional demo data. Do not use real student personal data in this public demo.

All records are fictional demo data. Do not use real student personal data in this public demo.

## Features

- Separate teacher and student sign-in and role-specific dashboards
- 60 fictional student profiles with six course-level metric records each (360 initial course records)
- Six distinct teacher accounts; each teacher can browse the complete student directory and cohort-wide analytics
- Student directory and course-level academic metrics
- Attendance, assignment, assessment, and engagement indicators
- Early-warning scores with contributing factors and suggested interventions
- Teacher alert inbox with New / Reviewed / Resolved states
- Teacher can enter academic data; high-risk records create an alert
- Timetable, notices, course activity feed, attendance report, and recommendations
- Flask REST API, React + Vite UI, SQLAlchemy database layer
- SQLite for local development; PostgreSQL URL supported for deployment

## Local development

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

API runs at `http://localhost:5000`. The database is seeded automatically on first startup.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Optional frontend environment variable: `VITE_API_URL=http://localhost:5000/api`.

## Deploy on Render

1. Push this project folder to a new GitHub repository.
2. In Render, create a **Blueprint** and select the repository. The `backend/render.yaml` blueprint creates a Flask web service and managed PostgreSQL database.
3. Set `CLIENT_ORIGIN` on the API service to the exact deployed frontend origin (for example `https://your-site.onrender.com`). For multiple origins, separate them with commas.
4. Create a **Static Site** in Render for `frontend`:
   - Build command: `npm install && npm run build`
   - Publish directory: `dist`
   - Environment variable: `VITE_API_URL=https://YOUR-API-SERVICE.onrender.com/api`
5. Trigger a redeploy of the frontend after setting `VITE_API_URL`. Trigger/restart the API after setting `CLIENT_ORIGIN`.
6. Visit the frontend URL and log in with one of the demo accounts above.

Render's free web service may sleep when idle; the first request after inactivity can be slow. Check current Render pricing/limits before choosing a database plan. If the managed PostgreSQL instance is not available on your plan, create a PostgreSQL database with a provider you have access to and set `DATABASE_URL` to its connection string.

## Prediction method and limitations

The current baseline is an interpretable weighted score derived from attendance, assignment average, assessment average, and engagement, with High / Moderate / Low bands. It is a **prototype early-warning heuristic**, not a trained TensorFlow model and not a validated dropout predictor. Thresholds are documented in `backend/app.py` (`predict`). Before real-world use, collect approved historical outcomes, validate model performance and fairness, add consent/access controls, audit logs, data retention policies, and a faculty review process. Do not automatically penalize students based on the score.

## Project alignment

This prototype covers the requested interactive dashboard, student performance prediction module, personalized recommendation baseline, and technical documentation. The supplied screenshots' academic portal structure is represented with course activities, profile identity, timetable, notifications, and attendance analytics. It is a standalone prototype and is not connected to Alliance University's real AUERP or Alliance.ai systems.

## Added academic workflows

- Relational `Course` and `Enrollment` tables with a teacher course-assignment action.
- Teacher attendance register supports present/absent/late records and correction by student/course/date.
- Teachers create assignments with course, description, maximum score, and deadline.
- Students can submit once before the deadline; the API rejects late submissions even if a student bypasses the UI.
- Teachers can set each student's score and feedback individually, validated against the assignment maximum.
- New API routes: `GET /api/courses`, `POST /api/courses/assign`, `GET/POST /api/attendance`, `GET/POST /api/assignments`, `POST /api/assignments/<id>/submit`, and `PATCH /api/submissions/<id>/score`.

The app remains a prototype with fictional seeded data. Review authentication/authorization, audit logging, migrations, and privacy requirements before using real student records.
