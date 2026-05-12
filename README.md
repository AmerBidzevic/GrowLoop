# GrowLoop

GrowLoop is our web application for building habits in a more motivating way. We built it around a simple daily loop: users create routines, complete habits, earn XP, unlock achievements, review their progress, and get smart recommendations when the app detects patterns in their activity.

We chose a web application because the project requirements allow either a web-based or mobile application. For the database, we use SQLite. It is simple to run locally, works well for the size of this project, and still gives us a real relational database with tables, foreign keys, and persistent data.

## Milestone 3 Scope

The current release contains the main GrowLoop functionality that we planned for the final milestone:

- User registration and login
- Onboarding questionnaire
- Habit create, read, update, delete
- Pause and resume habits
- Habit details and completion history
- Habit completion and 10 XP reward
- Streak tracking
- Level progression
- Achievements
- Analytics with weekly and monthly summaries
- Notification preferences
- Smart recommendation logic for suggestions, burnout detection, adaptive difficulty, and habit load guidance
- Responsive frontend
- 5 automated backend/API tests
- Render deployment configuration

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

## Run Tests

```powershell
python -m unittest discover -s tests -v
```

## Main API Endpoints

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
- `GET /api/recommendations`
- `GET /api/notification-preferences`
- `PUT /api/notification-preferences`

## Architecture and Patterns

- Architectural pattern: layered architecture. We separated the frontend, API routes, service logic, repository/database access, and SQLite persistence.
- Design pattern: Repository Pattern. `backend/repository.py` keeps database access in one place instead of spreading SQL through the route handlers.
- Design pattern: Strategy Pattern. `backend/services.py` separates the recommendation strategies for habit suggestions, burnout detection, adaptive difficulty, and habit improvement guidance.

## Database

GrowLoop uses SQLite. These are the main entities:

- `users`
- `onboarding_answers`
- `habits`
- `habit_completions`
- `achievements`
- `notification_preferences`

For Render deployment, `render.yaml` configures a persistent disk and sets `GROWLOOP_DB_PATH=/var/data/growloop.sqlite3`, so the SQLite file is stored outside the temporary application folder.

## Render Deployment

Recommended Render settings:

- Service type: Web Service
- Runtime: Python
- Build command: leave empty
- Start command: `python backend/server.py`
- Environment variable: `GROWLOOP_DB_PATH=/var/data/growloop.sqlite3`
- Persistent disk: mount path `/var/data`
