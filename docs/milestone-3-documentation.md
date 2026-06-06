# GrowLoop Third Milestone Documentation Notes

## Application Type

GrowLoop is a web-based application. We chose this format because the project requirements allow either a web-based or mobile application, and a responsive web interface was the most practical option for our team. The frontend communicates with the backend through REST API endpoints.

## Database Choice

GrowLoop uses SQLite as the database system. We selected SQLite because it gives us a real relational database while keeping the project easy to run locally. It also avoids extra setup for a separate database server.

Current database entities:

- `users`
- `onboarding_answers`
- `habits`
- `habit_completions`
- `achievements`
- `notification_preferences`
- `sessions`

For deployment on Render, SQLite should use a persistent disk. The included `render.yaml` stores the database at `/var/data/growloop.sqlite3`, which keeps the database file outside Render's temporary app folder.

## Completed Functionalities

- User registration
- User login
- Onboarding questionnaire
- Create habit
- Edit habit
- Delete habit
- Pause and resume habit
- View habit details
- Completion history
- Complete habit
- Earn XP
- Habit streaks
- Level progression
- Achievements
- Achievement details through the achievements list
- Analytics dashboard
- Weekly reflection summary
- Monthly performance summary
- Notification preferences
- Browser habit reminders based on saved reminder times
- Rule-based smart habit suggestions
- Adaptive difficulty recommendation
- Burnout detection
- Habit improvement suggestions
- Habit load recommendation
- Responsive web interface

## Architectural and Design Patterns

### Architectural Pattern: Layered Architecture

The application is organized into layers:

- Frontend layer: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`
- API/controller layer: `backend/server.py`
- Service layer: `backend/services.py`
- Repository layer: `backend/repository.py`
- Database layer: SQLite through `backend/database.py`

This structure separates the user interface, API routing, business logic, database access, and persistence.

### Design Pattern 1: Repository Pattern

`GrowLoopRepository` in `backend/repository.py` centralizes database operations. This prevents SQL queries from being spread across route handlers and makes the backend easier to test and maintain.

### Design Pattern 2: Strategy Pattern

`RecommendationEngine` in `backend/services.py` groups separate recommendation strategies:

- Habit suggestions
- Burnout detection
- Adaptive difficulty
- Habit improvement suggestions
- Habit load recommendation

These strategies solve the smart recommendation part of the project without requiring external API keys.

## Tests

The project includes five meaningful automated tests in `tests/test_api.py`:

1. Registration, login, and profile retrieval
2. Habit CRUD and pause/resume
3. Completion, XP, and achievement unlock
4. Analytics and smart recommendations
5. Notification preferences

Run tests with:

```powershell
python -m unittest discover -s tests -v
```

## Coding Standards

- Python code uses clear service and repository separation.
- SQL access is centralized in the repository layer.
- REST endpoints return JSON responses with appropriate HTTP status codes.
- Frontend JavaScript uses small functions for API calls, rendering, and UI actions.
- User input is validated on the backend before database changes.
- Passwords are stored as PBKDF2 hashes, not plain text.
- Logged-in API requests use server-side session tokens.

## Deployment

Render is the recommended deployment platform.

Suggested Render setup:

- Web Service
- Python runtime
- Build command: empty
- Start command: `python backend/server.py`
- Environment variable: `GROWLOOP_DB_PATH=/var/data/growloop.sqlite3`
- Persistent disk mounted at `/var/data`

After deployment, add the public Render URL to the final project documentation.

## Individual Contributions

Final contribution notes can be adjusted before LMS submission. Example format:

- Amer Bidzevic: backend implementation, database design, API testing, deployment setup.
- Emel Coloman: frontend implementation, UI testing, documentation, screenshots.
