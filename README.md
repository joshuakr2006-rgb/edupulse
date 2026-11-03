# EduPulse — Smart Education Monitoring & Analytics Platform

EduPulse is a role-based academic monitoring and analytics platform for teachers and students. It combines a React frontend, a Flask REST API, SQLAlchemy data access, PostgreSQL persistence in production, assignment file uploads, and an ML-based academic-risk prediction component.

## Live deployment

- **Frontend:** https://edupulse-frontend-vi2x.onrender.com
- **Backend API:** https://edupulse-l9io.onrender.com
- **Health check:** https://edupulse-l9io.onrender.com/api/health
- **Source repository:** https://github.com/joshuakr2006-rgb/edupulse

The deployed application uses the existing Render web services and PostgreSQL database. Do not create a second database or replace the existing production database when updating this project.

## Main capabilities

### Authentication and role-based dashboards
- Separate teacher and student sign-in.
- Role-specific dashboards and navigation.
- Student accounts can be created by a teacher from the student-management area.
- Teacher account initialization can be configured through backend environment variables.

### Teacher workflows
- Create and manage student accounts.
- Manage courses and student course assignments.
- View student and course academic information.
- Record and correct attendance.
- Create assignments with descriptions, maximum scores, and deadlines.
- Review student submissions, download submitted files, enter scores, and provide feedback.
- View academic indicators and risk information.

### Student workflows
- Access a student-specific dashboard.
- View courses, attendance, assessments, and assignments available to the account.
- Submit assignment files before the deadline.
- View grading results and teacher feedback.

### Assignment uploads
- Up to 5 files per submission.
- Maximum 20 MB per file.
- Maximum 50 MB combined per submission.
- Supported formats include PDF, DOC/DOCX, JPG/JPEG/PNG, TXT, RTF, ODT, XLS/XLSX/CSV, PPT/PPTX, and ZIP.
- The backend enforces upload limits and assignment deadlines; client-side checks alone are not relied upon.
- Production uploads should be stored on the Render persistent disk mounted at `/var/data`, using `UPLOAD_DIR=/var/data/uploads`.

### ML academic-risk prediction
- The backend loads a bundled Random Forest model from `backend/student_risk_model.joblib`.
- The model uses four academic indicators: attendance, assignment average, assessment average, and engagement.
- The prediction classes are **Low**, **Moderate**, and **High**.
- `backend/train_model.py` contains the model-training workflow.

**Model limitation:** The bundled model was trained using synthetic/example data. It is a working technical prototype, not a model validated on real Alliance University student outcomes. Predictions should be treated as decision-support signals, reviewed by faculty, and never used as the sole basis for academic penalties or consequential decisions. Real deployment requires institution-approved data, validation, fairness evaluation, privacy controls, and ongoing monitoring.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, JavaScript, CSS |
| Backend | Python, Flask, Flask-CORS |
| API | REST endpoints |
| ORM / database layer | Flask-SQLAlchemy, SQLAlchemy |
| Production database | PostgreSQL |
| Local development database | SQLite (through `DATABASE_URL`) |
| Authentication | JWT |
| ML | scikit-learn, Random Forest, joblib, NumPy |
| Production hosting | Render |

## Repository structure

```text
edupulse/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── student_risk_model.joblib
│   └── train_model.py
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       └── style.css
├── .gitignore
├── README.md
└── render.yaml
```

Runtime files such as `.env`, virtual environments, `node_modules`, local database files, and uploaded files must not be committed.

## Local development

### Requirements

- Python 3.12 recommended (the production Render runtime is configured for Python 3.12).
- Node.js and npm.
- Git.

### 1. Clone the repository

```bash
git clone https://github.com/joshuakr2006-rgb/edupulse.git
cd edupulse
```

### 2. Configure and run the backend

```bash
cd backend
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**
```bash
source .venv/bin/activate
```

Install dependencies and create a local environment file:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set local values. For example:

```dotenv
PORT=5000
DATABASE_URL=sqlite:///education.db
JWT_SECRET=replace-with-a-long-random-secret
CLIENT_ORIGIN=http://localhost:5173
UPLOAD_DIR=./uploads
MAX_FILES_PER_SUBMISSION=5
MAX_FILE_SIZE_MB=20
MAX_TOTAL_UPLOAD_MB=50
```

Do not commit `.env` or place real credentials in source control.

Start the API:

```bash
python app.py
```

The API runs locally at `http://localhost:5000`. Check `http://localhost:5000/api/health` for the health response.

### 3. Configure and run the frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm ci
```

Create `frontend/.env` if needed:

```dotenv
VITE_API_URL=http://localhost:5000/api
```

Start the Vite development server:

```bash
npm run dev
```

Open `http://localhost:5173`.

For a production build:

```bash
npm run build
```

The generated frontend assets are written to `frontend/dist/`.

## Production deployment on Render

The current production deployment is connected to the existing GitHub repository and existing Render resources. Update those resources rather than creating a new Blueprint or database.

### Existing services

- Backend web service: `edupulse-l9io`
- Frontend static site: `edupulse-frontend-vi2x`
- Existing PostgreSQL database: `edupulse-db`

### Backend service configuration

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Health check path: `/api/health`
- Python runtime: 3.12

Configure the following environment variables in the backend service:

| Variable | Purpose |
|---|---|
| `PYTHON_VERSION` | Python runtime; currently `3.12.4` |
| `DATABASE_URL` | Connection string for the existing PostgreSQL database |
| `JWT_SECRET` | Long, random secret used for JWT signing |
| `CLIENT_ORIGIN` | Exact deployed frontend origin |
| `UPLOAD_DIR` | `/var/data/uploads` for persistent uploads |
| `MAX_FILES_PER_SUBMISSION` | `5` |
| `MAX_FILE_SIZE_MB` | `20` |
| `MAX_TOTAL_UPLOAD_MB` | `50` |
| `INITIAL_TEACHER_EMAIL` | Email for initial teacher account setup, if needed |
| `INITIAL_TEACHER_PASSWORD` | Strong initial teacher password, if needed |
| `INITIAL_TEACHER_NAME` | Display name for initial teacher account, if needed |
| `PURGE_LEGACY_DEMO_DATA` | Keep disabled unless a deliberate, backed-up cleanup is required |

Never publish secret values in this README, GitHub, screenshots, or chat.

### Persistent file storage

The backend service needs a persistent disk mounted at `/var/data` for uploaded assignment files. Set `UPLOAD_DIR=/var/data/uploads`. Confirm the disk is attached to the existing backend service; a successful deployment by itself does not prove uploaded files survive restarts. Do not store production uploads in an ephemeral application directory.

### Frontend static site configuration

- Root directory: `frontend`
- Build command: `npm ci && npm run build`
- Publish directory: `dist`
- Environment variable:

```dotenv
VITE_API_URL=https://edupulse-l9io.onrender.com/api
```

After changing frontend environment variables, trigger a new frontend build/deploy. After changing backend environment variables, redeploy or restart the existing backend service as required by Render.

### Deployment verification checklist

1. Confirm the backend deployment is **Live**.
2. Open `https://edupulse-l9io.onrender.com/api/health` and confirm the API reports a healthy status and the ML model is loaded.
3. Open the frontend and sign in with an existing account.
4. Verify teacher and student access separately.
5. Verify a database write and read using a test record.
6. Verify assignment upload, download, grading, and feedback.
7. Confirm uploaded files remain available after a backend restart or redeployment.
8. Confirm the frontend is using the deployed API URL.

## Security, privacy, and operational notes

- Do not commit `.env`, database credentials, JWT secrets, passwords, local database files, virtual environments, `node_modules`, or uploaded student documents.
- Use strong, unique passwords for teacher and student accounts.
- Do not use real student data in a public demonstration without institutional approval and appropriate privacy safeguards.
- Restrict access to student records and uploaded submissions to authorized users.
- Back up the production database before schema or data migrations.
- Keep `PURGE_LEGACY_DEMO_DATA` disabled unless the intended cleanup has been reviewed and a backup exists.
- The Render Free plan may have usage, sleep, storage, and database-retention limitations. Check the current service and database status in Render before relying on the deployment for long-term storage.

## Project status and limitations

The frontend and backend have been deployed to Render, the API health endpoint has been checked, the ML artifact has loaded in production, and teacher/student sign-in has been exercised. The live PostgreSQL database was queried successfully and contained one teacher account and one student account at the time of verification.

The full production workflow—especially multi-file upload persistence, deadline enforcement, teacher grading, and end-to-end ML predictions—should still be tested in the deployed environment before describing the system as fully production-ready.

EduPulse is an independent academic prototype. It is not connected to, endorsed by, or an official replacement for Alliance University's AUERP or Alliance.ai systems.
