# GrowLoop

GrowLoop is a gamified habit-building application for tracking daily routines, completing habits, and earning XP.

## Milestone 2 Scope

This initial release implements the Release 1.0 core loop:

- User registration and login
- Onboarding questionnaire
- Habit creation and listing
- Habit completion
- XP reward after completion
- SQLite persistence through REST API endpoints

## Project Structure

```text
backend/     Python REST API and SQLite database setup
frontend/    Responsive customer-facing web interface
docs/        ER diagram and milestone documentation assets
```

## Run Locally

From the repository root:

```powershell
python backend/server.py
```

Then open:

```text
http://localhost:8000
```

The backend serves REST API routes under `/api/*` and serves the frontend from the `frontend` folder.

## Main REST Endpoints

- `POST /api/register`
- `POST /api/login`
- `POST /api/onboarding`
- `GET /api/habits`
- `POST /api/habits`
- `GET /api/habits/{id}`
- `PUT /api/habits/{id}`
- `DELETE /api/habits/{id}`
- `POST /api/habits/{id}/complete`

