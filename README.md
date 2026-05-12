# GrowLoop

GrowLoop is a responsive web application for gamified habit building. Users can create routines, complete habits, earn XP, unlock achievements, and review analytics.

The project is a web app, which is allowed by the SE project requirements because the project can be either web-based or mobile. The database is SQLite, which is acceptable for this course-sized project and is documented as the chosen DBMS.

## Release 2.0 Scope

This branch represents Release 2.0 - Engagement Engine. It builds on Release 1.0 with complete habit management, gamification, analytics, and basic reminder storage.

- Habit create, read, update, delete
- Pause and resume habits
- Habit details and completion history
- Habit completion and 10 XP reward
- Streak tracking
- Level progression
- Achievements
- Analytics with weekly and monthly summaries
- Reminder time storage on habits
- Responsive frontend

## Project Structure

```text
backend/     Python REST API and SQLite database setup
frontend/    Responsive customer-facing web interface
docs/        ER diagram and milestone documentation assets
tests/       Automated API tests
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

## Test Locally

```powershell
python -m unittest discover -s tests -v
```

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
- `POST /api/habits/{id}/pause`
- `POST /api/habits/{id}/resume`
- `GET /api/analytics`
- `GET /api/achievements`

## Architecture and Patterns

- Architectural pattern: layered architecture. The app separates frontend, HTTP routes, service logic, repository/database access, and SQLite persistence.
- Design pattern: Repository Pattern in `backend/repository.py` centralizes database access.
- Design pattern: service layer in `backend/services.py` separates analytics, achievement, authentication, and habit behavior from HTTP routing.

## Database

GrowLoop uses SQLite. Main entities:

- `users`
- `onboarding_answers`
- `habits`
- `habit_completions`
- `achievements`
