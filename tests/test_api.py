import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def free_port():
    sock = socket.socket()
    sock.bind(("localhost", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class GrowLoopApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.port = free_port()
        cls.base_url = f"http://localhost:{cls.port}"
        env = os.environ.copy()
        env["PORT"] = str(cls.port)
        env["HOST"] = "localhost"
        env["GROWLOOP_DB_PATH"] = str(Path(cls.temp_dir.name) / "test.sqlite3")
        cls.server = subprocess.Popen(
            [sys.executable, "backend/server.py"],
            cwd=ROOT_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cls.wait_for_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
        cls.temp_dir.cleanup()

    @classmethod
    def wait_for_server(cls):
        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                cls.request("/api/health")
                return
            except Exception:
                time.sleep(0.2)
        stdout, stderr = cls.server.communicate(timeout=1)
        raise RuntimeError(f"Server failed to start\nSTDOUT: {stdout}\nSTDERR: {stderr}")

    @classmethod
    def request(cls, path, method="GET", payload=None, user_id=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(cls.base_url + path, data=body, method=method)
        request.add_header("Content-Type", "application/json")
        if user_id:
            request.add_header("X-User-Id", str(user_id))
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def create_user(self, suffix):
        email = f"user{suffix}@growloop.test"
        status, _payload = self.request(
            "/api/register",
            "POST",
            {"username": f"User {suffix}", "email": email, "password": "Secret123!"},
        )
        self.assertEqual(status, 201)
        status, user = self.request("/api/login", "POST", {"email": email, "password": "Secret123!"})
        self.assertEqual(status, 200)
        return user

    def create_habit(self, user_id, name="Read"):
        status, habit = self.request(
            "/api/habits",
            "POST",
            {
                "name": name,
                "description": "Read before work",
                "category": "Learning",
                "frequency": "Daily",
                "target_time": "08:00",
                "difficulty": "Easy",
                "reminder": "07:55",
            },
            user_id,
        )
        self.assertEqual(status, 201)
        return habit["id"]

    def test_registration_login_and_profile(self):
        user = self.create_user("auth")
        self.assertEqual(user["level"], 1)
        status, profile = self.request("/api/profile", user_id=user["id"])
        self.assertEqual(status, 200)
        self.assertEqual(profile["email"], "userauth@growloop.test")

    def test_habit_crud_and_pause_resume(self):
        user = self.create_user("crud")
        habit_id = self.create_habit(user["id"])
        status, _payload = self.request(
            f"/api/habits/{habit_id}",
            "PUT",
            {
                "name": "Read 25 pages",
                "description": "Updated routine",
                "category": "Learning",
                "frequency": "Daily",
                "target_time": "08:15",
                "difficulty": "Medium",
                "reminder": "08:00",
            },
            user["id"],
        )
        self.assertEqual(status, 200)
        status, _payload = self.request(f"/api/habits/{habit_id}/pause", "POST", {}, user["id"])
        self.assertEqual(status, 200)
        status, habits = self.request("/api/habits?include_inactive=1", user_id=user["id"])
        self.assertFalse(habits[0]["is_active"])
        status, _payload = self.request(f"/api/habits/{habit_id}/resume", "POST", {}, user["id"])
        self.assertEqual(status, 200)
        status, _payload = self.request(f"/api/habits/{habit_id}", "DELETE", user_id=user["id"])
        self.assertEqual(status, 200)

    def test_completion_awards_xp_and_achievement(self):
        user = self.create_user("xp")
        habit_id = self.create_habit(user["id"])
        status, result = self.request(f"/api/habits/{habit_id}/complete", "POST", {}, user["id"])
        self.assertEqual(status, 200)
        self.assertEqual(result["xp"], 10)
        status, achievements = self.request("/api/achievements", user_id=user["id"])
        self.assertEqual(status, 200)
        self.assertTrue(any(item["code"] == "FIRST_STEP" and item["unlocked"] for item in achievements))

    def test_analytics_and_recommendations(self):
        user = self.create_user("smart")
        self.request(
            "/api/onboarding",
            "POST",
            {"goals": "Health", "schedule": "Morning focused", "habit_count": 2},
            user["id"],
        )
        habit_id = self.create_habit(user["id"], "Walk")
        self.request(f"/api/habits/{habit_id}/complete", "POST", {}, user["id"])
        status, analytics = self.request("/api/analytics", user_id=user["id"])
        self.assertEqual(status, 200)
        self.assertEqual(analytics["total_completions"], 1)
        status, recommendations = self.request("/api/recommendations", user_id=user["id"])
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(recommendations["habit_suggestions"]), 1)

    def test_notification_preferences(self):
        user = self.create_user("settings")
        status, prefs = self.request("/api/notification-preferences", user_id=user["id"])
        self.assertEqual(status, 200)
        self.assertEqual(prefs["habit_reminders"], 1)
        status, updated = self.request(
            "/api/notification-preferences",
            "PUT",
            {
                "habit_reminders": False,
                "inactivity_alerts": True,
                "weekly_summary": False,
                "monthly_summary": True,
            },
            user["id"],
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["habit_reminders"], 0)
        self.assertEqual(updated["monthly_summary"], 1)


if __name__ == "__main__":
    unittest.main()
