# Olympia — Olympiad management

Olympia is a local-first MVP for managing olympiad directions, students, daily attendance, event dates, and attendance statistics. The API is FastAPI + SQLAlchemy 2.0; the responsive React/TypeScript frontend is designed around quick attendance marking.

## Run the static frontend and API with Docker Compose

Requirements: Docker Engine/Desktop with Compose v2.

```sh
cp .env.example .env
# Set JWT_SECRET and SEED_ADMIN_PASSWORD in .env before using outside local development.
docker compose up --build
```

The default `compose.yaml` builds the frontend into static files and serves them with Nginx. Open the frontend at <http://localhost:5173> and API docs at <http://localhost:8000/docs>.

For frontend and backend hot reload during development, use the separate development stack:

```sh
docker compose -f compose.dev.yaml up --build
```

For a public deployment, set `VITE_API_URL` to the public HTTPS API URL and `CORS_ORIGINS` to the exact HTTPS frontend origin before building. The frontend API URL is embedded at build time, so rebuild the frontend after changing it.

## Deploy the frontend and API to Vercel with Supabase Postgres

Use two Vercel projects linked to this repository:

1. Create the frontend project with Root Directory `frontend`. Vercel detects Vite and builds the static site.
2. Create the API project with Root Directory `backend`. `backend/index.py` exposes the FastAPI application to Vercel.
3. In Supabase, create a project and copy its **Transaction pooler** connection string from Connect. Set it as the API project's `DATABASE_URL`. The API supports the Supabase pooler with SSL, SQLAlchemy `NullPool`, and Psycopg prepared statements disabled.
4. Set the API project's `JWT_SECRET` and `CORS_ORIGINS` (the exact frontend HTTPS origin) in Vercel. Set `VITE_API_URL` in the frontend project to the API project's HTTPS URL. Vite embeds this variable during the build, so redeploy the frontend after changing it.
5. Run Alembic once against the Supabase database before serving requests: `cd backend`, install `requirements.txt`, set `DATABASE_URL` to the Supabase direct or session-pooler connection string, then run `alembic upgrade head`. For a new database, run `python -m app.seed` once with the intended seed passwords configured. Do not run migrations or seeding when a Vercel function starts.

Keep database credentials and `JWT_SECRET` in Vercel's backend environment settings. Never put them in a `VITE_` variable or commit them. Keep Docker Compose for local development; Vercel does not run the Compose stack or its Postgres container.

The seed creates the global administrator (`admin`) and three Olympiad Leads (`dias`, `kali`, `arman`), plus Mathematics, Physics, Chemistry, Biology, and English directions. Physics, Chemistry, and Mathematics are assigned to Dias, Kali, and Arman. Biology and English are unassigned. All seed passwords are configurable and default to `admin123` and `lead1234` for local development. The seed adds no students or attendance.

Change the seed passwords before exposing the service. The seed is idempotent and does not reset existing passwords or create sample students or attendance.

## Local development

Requirements: Python 3.12+, Node 20+, PostgreSQL 16+ (SQLite can be used for backend-only development).

Backend:

```sh
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://olympiad:olympiad_dev@localhost:5432/olympiad'
export JWT_SECRET='replace-with-a-long-random-secret'
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Frontend in another terminal:

```sh
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

## Configuration

| Variable | Purpose | Local default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy database connection | SQLite in `backend/` |
| `JWT_SECRET` | JWT signing key | Development-only fallback; replace it |
| `SEED_ADMIN_PASSWORD` | Initial admin password | `admin123` |
| `SEED_LEAD_PASSWORD` | Initial Olympiad Lead password | `lead1234` |
| `POSTGRES_PASSWORD` | Compose database password | `olympiad_dev` |
| `CORS_ORIGINS` | Comma-separated frontend origins | `http://localhost:5173` |
| `APP_TIMEZONE` | Timezone used for dashboard “today” | `Asia/Almaty` |
| `VITE_API_URL` | API URL used by the browser | `http://localhost:8000` |

## Migrations and seed data

Alembic migrations live in `backend/alembic`. Run `alembic upgrade head` after setting `DATABASE_URL`. For a new database, run `python -m app.seed`. The seed creates the admin, three leads, and five requested directions; add students, events, and attendance through the application.

## Tests

From `backend/`, install requirements and run:

```sh
pytest
```

Tests cover login, authenticated identity, role and group boundaries, direction/student creation, attendance upsert and duplicate request protection, statistics, and calendar permissions.

## MVP scope

- Roles are `GLOBAL_ADMIN` and `OLYMPIAD_LEAD`. Students do not log in.
- Leads can manage students and attendance in their assigned direction. Calendar mutation and account management are admin-only.
- Students are deactivated instead of physically deleted; historical attendance is retained.
- Attendance stores a local calendar `date`, the marker, and one record per student/date.
- Backend authorization is enforced on API routes independently of the frontend navigation.
- Dashboard, student list, quick attendance, statistics, and monthly calendar are included. The schema and REST endpoints are intended to support later expansion.
