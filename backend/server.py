from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import json
import mimetypes
import os
import re

from database import initialize_database
from repository import GrowLoopRepository
from services import (
    AchievementService,
    AnalyticsService,
    AuthService,
    HabitService,
    RecommendationEngine,
    enrich_profile,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))


class GrowLoopHandler(BaseHTTPRequestHandler):
    repo = GrowLoopRepository()
    auth_service = AuthService(repo)
    habit_service = HabitService(repo)
    analytics_service = AnalyticsService(repo)
    achievement_service = AchievementService(repo)
    recommendation_engine = RecommendationEngine()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_get(parsed.path, parse_qs(parsed.query))
        else:
            self.serve_static(parsed.path)

    def do_POST(self):
        self.handle_api_write("POST")

    def do_PUT(self):
        self.handle_api_write("PUT")

    def do_DELETE(self):
        self.handle_api_write("DELETE")

    def handle_api_get(self, path, query):
        if path == "/api/health":
            self.send_json({"status": "ok"})
            return

        if path == "/api/profile":
            user_id = self.require_user_id()
            if user_id is None:
                return
            self.send_json(enrich_profile(self.repo.get_user(user_id)))
            return

        if path == "/api/habits":
            user_id = self.require_user_id()
            if user_id is None:
                return
            include_inactive = query.get("include_inactive", ["0"])[0] == "1"
            self.send_json(self.habit_service.list_habits(user_id, include_inactive))
            return

        habit_match = re.fullmatch(r"/api/habits/(\d+)", path)
        if habit_match:
            user_id = self.require_user_id()
            if user_id is None:
                return
            habit = self.habit_service.get_habit_details(user_id, int(habit_match.group(1)))
            if not habit:
                self.send_error_json(404, "Habit not found")
                return
            self.send_json(habit)
            return

        if path == "/api/analytics":
            user_id = self.require_user_id()
            if user_id is None:
                return
            self.send_json(self.analytics_service.dashboard(user_id))
            return

        if path == "/api/achievements":
            user_id = self.require_user_id()
            if user_id is None:
                return
            self.send_json(self.achievement_service.list_with_locked(user_id))
            return

        if path == "/api/recommendations":
            user_id = self.require_user_id()
            if user_id is None:
                return
            habits = self.habit_service.list_habits(user_id, include_inactive=True)
            completions = self.repo.list_completions(user_id, limit=100)
            onboarding = self.repo.get_onboarding(user_id)
            self.send_json(self.recommendation_engine.dashboard(onboarding, habits, completions))
            return

        if path == "/api/notification-preferences":
            user_id = self.require_user_id()
            if user_id is None:
                return
            self.send_json(self.repo.get_notification_preferences(user_id))
            return

        self.send_error_json(404, "API route not found")

    def handle_api_write(self, method):
        parsed = urlparse(self.path)
        path = parsed.path
        data = self.read_json_body() if method in {"POST", "PUT"} else {}

        if path == "/api/register" and method == "POST":
            if missing_fields(data, ["username", "email", "password"]):
                self.send_error_json(400, "All fields are required")
                return
            try:
                payload = self.auth_service.register(data)
                self.send_json(payload, 201)
            except Exception:
                self.send_error_json(409, "Email already registered")
            return

        if path == "/api/login" and method == "POST":
            if missing_fields(data, ["email", "password"]):
                self.send_error_json(400, "Enter user data")
                return
            user = self.auth_service.login(data["email"], data["password"])
            if not user:
                self.send_error_json(401, "Invalid email or password")
                return
            self.send_json(user)
            return

        if path == "/api/logout" and method == "POST":
            token = self.get_session_token()
            if token:
                self.repo.delete_session(token)
            self.send_json({"message": "Logged out"})
            return

        if path == "/api/onboarding" and method == "POST":
            user_id = self.require_user_id()
            if user_id is None:
                return
            if missing_fields(data, ["goals", "schedule", "habit_count"]):
                self.send_error_json(400, "All onboarding questions are required")
                return
            self.repo.save_onboarding(user_id, data["goals"], data["schedule"], data["habit_count"])
            suggestions = self.recommendation_engine.suggestions(self.repo.get_onboarding(user_id))
            self.send_json({"message": "Onboarding saved", "suggestions": suggestions})
            return

        if path == "/api/habits" and method == "POST":
            user_id = self.require_user_id()
            if user_id is None:
                return
            if missing_fields(data, ["name", "category", "frequency", "target_time", "difficulty"]):
                self.send_error_json(400, "All fields except reminder are required")
                return
            habit_id = self.habit_service.create_habit(user_id, data)
            self.send_json({"id": habit_id, "message": "Habit created"}, 201)
            return

        complete_match = re.fullmatch(r"/api/habits/(\d+)/complete", path)
        if complete_match and method == "POST":
            user_id = self.require_user_id()
            if user_id is None:
                return
            try:
                profile = self.habit_service.complete_habit(user_id, int(complete_match.group(1)))
            except Exception:
                self.send_error_json(409, "Habit already completed today")
                return
            if not profile:
                self.send_error_json(404, "Habit not found")
                return
            self.send_json({"message": "Habit completed", **profile})
            return

        active_match = re.fullmatch(r"/api/habits/(\d+)/(pause|resume)", path)
        if active_match and method == "POST":
            user_id = self.require_user_id()
            if user_id is None:
                return
            is_active = active_match.group(2) == "resume"
            changed = self.habit_service.set_active(user_id, int(active_match.group(1)), is_active)
            if changed == 0:
                self.send_error_json(404, "Habit not found")
                return
            self.send_json({"message": "Habit resumed" if is_active else "Habit paused"})
            return

        habit_match = re.fullmatch(r"/api/habits/(\d+)", path)
        if habit_match and method in {"PUT", "DELETE"}:
            user_id = self.require_user_id()
            if user_id is None:
                return
            habit_id = int(habit_match.group(1))
            if method == "PUT":
                if missing_fields(data, ["name", "category", "frequency", "target_time", "difficulty"]):
                    self.send_error_json(400, "All fields except reminder are required")
                    return
                changed = self.habit_service.update_habit(user_id, habit_id, data)
                if changed == 0:
                    self.send_error_json(404, "Habit not found")
                    return
                self.send_json({"message": "Habit updated"})
                return

            changed = self.habit_service.delete_habit(user_id, habit_id)
            if changed == 0:
                self.send_error_json(404, "Habit not found")
                return
            self.send_json({"message": "Habit deleted"})
            return

        if path == "/api/notification-preferences" and method == "PUT":
            user_id = self.require_user_id()
            if user_id is None:
                return
            self.send_json(self.repo.update_notification_preferences(user_id, data))
            return

        self.send_error_json(404, "API route not found")

    def require_user_id(self):
        token = self.get_session_token()
        if token:
            user = self.repo.find_session_user(token)
            if user:
                return user["id"]

        # Backward-compatible fallback for local tests and earlier release branches.
        raw_user_id = self.headers.get("X-User-Id")
        if raw_user_id and raw_user_id.isdigit():
            return int(raw_user_id)

        if not token:
            self.send_error_json(401, "Authentication required")
            return None
        self.send_error_json(401, "Session expired or invalid")
        return None

    def get_session_token(self):
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.removeprefix("Bearer ").strip()
        return self.headers.get("X-Session-Token", "").strip()

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error_json(400, "Invalid JSON")
            return {}

    def serve_static(self, path):
        if path == "/":
            path = "/index.html"
        requested = (FRONTEND_DIR / path.lstrip("/")).resolve()
        if FRONTEND_DIR.resolve() not in requested.parents and requested != FRONTEND_DIR.resolve():
            self.send_error(403)
            return
        if not requested.exists() or requested.is_dir():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(requested.read_bytes())

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status, message):
        self.send_json({"error": message}, status)

    def log_message(self, format, *args):
        return


def missing_fields(data, fields):
    return any(not str(data.get(field, "")).strip() for field in fields)


if __name__ == "__main__":
    initialize_database()
    server = ThreadingHTTPServer((HOST, PORT), GrowLoopHandler)
    print(f"GrowLoop is running at http://{HOST}:{PORT}")
    server.serve_forever()
