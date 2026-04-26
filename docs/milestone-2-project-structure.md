# Milestone 2 Project Structure

## GitHub Repository

GitHub link: `Add repository URL here`

Collaborators to add:

- `Ajla115`
- `amilacausevic`

## Technologies

### Backend

- Python 3
- Built-in `http.server` for REST endpoints
- Built-in `sqlite3` for data persistence
- PBKDF2 password hashing through Python `hashlib`

### Frontend

- HTML5
- CSS3
- Vanilla JavaScript
- Responsive layout with CSS Grid and media queries

### Database

- SQLite database stored in `backend/growloop.sqlite3`

Database entities:

- `users`
- `onboarding_answers`
- `habits`
- `habit_completions`

### External API Integration

No external API integration is included in Milestone 2. AI-powered suggestions and notification integrations are planned for later releases according to the GrowLoop roadmap.

## Initial Release Features

This first release is aligned with GrowLoop Release 1.0 from the roadmap:

- US-1: User Registration
- US-2: User Login
- US-3: Onboarding Questionnaire
- US-4: Create a Habit
- US-7: Complete a Habit
- US-10 basic: Earn XP after habit completion
- NFR-2: Security through password hashing and user-scoped API access

## CRUD Operations

The application includes CRUD operations for habits:

- Create: `POST /api/habits`
- Read: `GET /api/habits` and `GET /api/habits/{id}`
- Update: `PUT /api/habits/{id}`
- Delete: `DELETE /api/habits/{id}`

Additional release endpoints:

- `POST /api/register`
- `POST /api/login`
- `POST /api/onboarding`
- `POST /api/habits/{id}/complete`

