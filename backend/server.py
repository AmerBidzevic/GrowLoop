from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import mimetypes
import re

from database import get_connection, hash_password, initialize_database, row_to_dict, verify_password


ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
HOST = "localhost"
PORT = 8000


class GrowLoopHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self.handle_api_get(path)
        else:
            self.serve_static(path)

    def do_POST(self):
        self.handle_api_write("POST")

    def do_PUT(self):
        self.handle_api_write("PUT")

    def do_DELETE(self):
        self.handle_api_write("DELETE")

    def handle_api_get(self, path):
        if path == "/api/habits":
            user_id = self.require_user_id()
            if user_id is None:
                return
            with get_connection() as conn:
                habits = conn.execute(
                    """
                    SELECT h.*,
                           CASE WHEN hc.id IS NULL THEN 0 ELSE 1 END AS completed_today
                    FROM habits h
                    LEFT JOIN habit_completions hc
                        ON hc.habit_id = h.id AND hc.completed_on = CURRENT_DATE
                    WHERE h.user_id = ? AND h.is_active = 1
                    ORDER BY h.created_at DESC
                    """,
                    (user_id,),
                ).fetchall()
            self.send_json([row_to_dict(habit) for habit in habits])
            return

        habit_match = re.fullmatch(r"/api/habits/(\d+)", path)
        if habit_match:
            user_id = self.require_user_id()
            if user_id is None:
                return
            habit_id = int(habit_match.group(1))
            with get_connection() as conn:
                habit = conn.execute(
                    "SELECT * FROM habits WHERE id = ? AND user_id = ?",
                    (habit_id, user_id),
                ).fetchone()
            if not habit:
                self.send_error_json(404, "Habit not found")
                return
            self.send_json(row_to_dict(habit))
            return

        if path == "/api/profile":
            user_id = self.require_user_id()
            if user_id is None:
                return
            with get_connection() as conn:
                user = conn.execute(
                    "SELECT id, username, email, xp FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
            self.send_json(row_to_dict(user))
            return

        self.send_error_json(404, "API route not found")

    def handle_api_write(self, method):
        path = urlparse(self.path).path
        data = self.read_json_body() if method in {"POST", "PUT"} else {}

        if path == "/api/register" and method == "POST":
            required = ["username", "email", "password"]
            if missing_fields(data, required):
                self.send_error_json(400, "All fields are required")
                return
            password_hash, password_salt = hash_password(data["password"])
            try:
                with get_connection() as conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO users (username, email, password_hash, password_salt)
                        VALUES (?, ?, ?, ?)
                        """,
                        (data["username"], data["email"].lower(), password_hash, password_salt),
                    )
                self.send_json({"id": cursor.lastrowid, "message": "Registration successful"}, 201)
            except Exception:
                self.send_error_json(409, "Email already registered")
            return

        if path == "/api/login" and method == "POST":
            if missing_fields(data, ["email", "password"]):
                self.send_error_json(400, "Enter user data")
                return
            with get_connection() as conn:
                user = conn.execute(
                    "SELECT * FROM users WHERE email = ?",
                    (data["email"].lower(),),
                ).fetchone()
            if not user or not verify_password(data["password"], user["password_hash"], user["password_salt"]):
                self.send_error_json(401, "Invalid email or password")
                return
            self.send_json({"id": user["id"], "username": user["username"], "xp": user["xp"]})
            return

        if path == "/api/onboarding" and method == "POST":
            user_id = self.require_user_id()
            if user_id is None:
                return
            if missing_fields(data, ["goals", "schedule", "habit_count"]):
                self.send_error_json(400, "All onboarding questions are required")
                return
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO onboarding_answers (user_id, goals, schedule, habit_count)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        goals = excluded.goals,
                        schedule = excluded.schedule,
                        habit_count = excluded.habit_count
                    """,
                    (user_id, data["goals"], data["schedule"], int(data["habit_count"])),
                )
            self.send_json({"message": "Onboarding saved"})
            return

        if path == "/api/habits" and method == "POST":
            user_id = self.require_user_id()
            if user_id is None:
                return
            required = ["name", "category", "frequency", "target_time", "difficulty"]
            if missing_fields(data, required):
                self.send_error_json(400, "All fields except reminder are required")
                return
            with get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO habits
                        (user_id, name, category, frequency, target_time, difficulty, reminder)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        data["name"],
                        data["category"],
                        data["frequency"],
                        data["target_time"],
                        data["difficulty"],
                        data.get("reminder", ""),
                    ),
                )
            self.send_json({"id": cursor.lastrowid, "message": "Habit created"}, 201)
            return

        complete_match = re.fullmatch(r"/api/habits/(\d+)/complete", path)
        if complete_match and method == "POST":
            user_id = self.require_user_id()
            if user_id is None:
                return
            habit_id = int(complete_match.group(1))
            with get_connection() as conn:
                habit = conn.execute(
                    "SELECT id FROM habits WHERE id = ? AND user_id = ?",
                    (habit_id, user_id),
                ).fetchone()
                if not habit:
                    self.send_error_json(404, "Habit not found")
                    return
                try:
                    conn.execute(
                        "INSERT INTO habit_completions (habit_id, user_id) VALUES (?, ?)",
                        (habit_id, user_id),
                    )
                    conn.execute("UPDATE users SET xp = xp + 10 WHERE id = ?", (user_id,))
                except Exception:
                    self.send_error_json(409, "Habit already completed today")
                    return
                user = conn.execute("SELECT xp FROM users WHERE id = ?", (user_id,)).fetchone()
            self.send_json({"message": "Habit completed", "xp": user["xp"]})
            return

        habit_match = re.fullmatch(r"/api/habits/(\d+)", path)
        if habit_match and method in {"PUT", "DELETE"}:
            user_id = self.require_user_id()
            if user_id is None:
                return
            habit_id = int(habit_match.group(1))
            if method == "PUT":
                required = ["name", "category", "frequency", "target_time", "difficulty"]
                if missing_fields(data, required):
                    self.send_error_json(400, "All fields except reminder are required")
                    return
                with get_connection() as conn:
                    cursor = conn.execute(
                        """
                        UPDATE habits
                        SET name = ?, category = ?, frequency = ?, target_time = ?,
                            difficulty = ?, reminder = ?
                        WHERE id = ? AND user_id = ?
                        """,
                        (
                            data["name"],
                            data["category"],
                            data["frequency"],
                            data["target_time"],
                            data["difficulty"],
                            data.get("reminder", ""),
                            habit_id,
                            user_id,
                        ),
                    )
                if cursor.rowcount == 0:
                    self.send_error_json(404, "Habit not found")
                    return
                self.send_json({"message": "Habit updated"})
                return

            with get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM habits WHERE id = ? AND user_id = ?",
                    (habit_id, user_id),
                )
            if cursor.rowcount == 0:
                self.send_error_json(404, "Habit not found")
                return
            self.send_json({"message": "Habit deleted"})
            return

        self.send_error_json(404, "API route not found")

    def require_user_id(self):
        raw_user_id = self.headers.get("X-User-Id")
        if not raw_user_id or not raw_user_id.isdigit():
            self.send_error_json(401, "Authentication required")
            return None
        return int(raw_user_id)

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

