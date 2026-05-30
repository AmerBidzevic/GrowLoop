from database import get_connection, row_to_dict
import hashlib


class GrowLoopRepository:
    """Repository Pattern: all database access is isolated behind this class."""

    def create_user(self, username, email, password_hash, password_salt):
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, email, password_hash, password_salt)
                VALUES (?, ?, ?, ?)
                """,
                (username, email.lower(), password_hash, password_salt),
            )
            conn.execute(
                "INSERT OR IGNORE INTO notification_preferences (user_id) VALUES (?)",
                (cursor.lastrowid,),
            )
            return cursor.lastrowid

    def find_user_by_email(self, email):
        with get_connection() as conn:
            return row_to_dict(conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone())

    def get_user(self, user_id):
        with get_connection() as conn:
            return row_to_dict(
                conn.execute(
                    "SELECT id, username, email, xp, created_at FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
            )

    def create_session(self, user_id, token, expires_at):
        token_hash = hash_token(token)
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
                (user_id, token_hash, expires_at),
            )

    def find_session_user(self, token):
        token_hash = hash_token(token)
        with get_connection() as conn:
            return row_to_dict(
                conn.execute(
                    """
                    SELECT u.id, u.username, u.email, u.xp, u.created_at
                    FROM sessions s
                    JOIN users u ON u.id = s.user_id
                    WHERE s.token_hash = ? AND s.expires_at > CURRENT_TIMESTAMP
                    """,
                    (token_hash,),
                ).fetchone()
            )

    def delete_session(self, token):
        token_hash = hash_token(token)
        with get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def save_onboarding(self, user_id, goals, schedule, habit_count):
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
                (user_id, goals, schedule, int(habit_count)),
            )

    def get_onboarding(self, user_id):
        with get_connection() as conn:
            return row_to_dict(
                conn.execute("SELECT * FROM onboarding_answers WHERE user_id = ?", (user_id,)).fetchone()
            )

    def create_habit(self, user_id, data):
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO habits
                    (user_id, name, description, category, frequency, target_time, difficulty, reminder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    data["name"],
                    data.get("description", ""),
                    data["category"],
                    data["frequency"],
                    data["target_time"],
                    data["difficulty"],
                    data.get("reminder", ""),
                ),
            )
            return cursor.lastrowid

    def list_habits(self, user_id, include_inactive=False):
        active_filter = "" if include_inactive else "AND h.is_active = 1"
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT h.*,
                       CASE WHEN today.id IS NULL THEN 0 ELSE 1 END AS completed_today,
                       COUNT(hc.id) AS completion_count,
                       COALESCE(MAX(hc.completed_on), '') AS last_completed_on
                FROM habits h
                LEFT JOIN habit_completions today
                    ON today.habit_id = h.id AND today.completed_on = CURRENT_DATE
                LEFT JOIN habit_completions hc
                    ON hc.habit_id = h.id
                WHERE h.user_id = ? {active_filter}
                GROUP BY h.id
                ORDER BY h.is_active DESC, h.created_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [row_to_dict(row) for row in rows]

    def get_habit(self, user_id, habit_id):
        with get_connection() as conn:
            return row_to_dict(
                conn.execute(
                    """
                    SELECT h.*,
                           CASE WHEN today.id IS NULL THEN 0 ELSE 1 END AS completed_today,
                           COUNT(hc.id) AS completion_count,
                           COALESCE(MAX(hc.completed_on), '') AS last_completed_on
                    FROM habits h
                    LEFT JOIN habit_completions today
                        ON today.habit_id = h.id AND today.completed_on = CURRENT_DATE
                    LEFT JOIN habit_completions hc
                        ON hc.habit_id = h.id
                    WHERE h.id = ? AND h.user_id = ?
                    GROUP BY h.id
                    """,
                    (habit_id, user_id),
                ).fetchone()
            )

    def update_habit(self, user_id, habit_id, data):
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE habits
                SET name = ?, description = ?, category = ?, frequency = ?, target_time = ?,
                    difficulty = ?, reminder = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    data["name"],
                    data.get("description", ""),
                    data["category"],
                    data["frequency"],
                    data["target_time"],
                    data["difficulty"],
                    data.get("reminder", ""),
                    habit_id,
                    user_id,
                ),
            )
            return cursor.rowcount

    def delete_habit(self, user_id, habit_id):
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id))
            return cursor.rowcount

    def set_habit_active(self, user_id, habit_id, is_active):
        with get_connection() as conn:
            cursor = conn.execute(
                "UPDATE habits SET is_active = ? WHERE id = ? AND user_id = ?",
                (1 if is_active else 0, habit_id, user_id),
            )
            return cursor.rowcount

    def complete_habit(self, user_id, habit_id):
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO habit_completions (habit_id, user_id) VALUES (?, ?)",
                (habit_id, user_id),
            )
            conn.execute("UPDATE users SET xp = xp + 10 WHERE id = ?", (user_id,))
            return row_to_dict(conn.execute("SELECT xp FROM users WHERE id = ?", (user_id,)).fetchone())

    def list_completions(self, user_id, habit_id=None, limit=100):
        params = [user_id]
        habit_filter = ""
        if habit_id is not None:
            habit_filter = "AND habit_id = ?"
            params.append(habit_id)
        params.append(limit)
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM habit_completions
                WHERE user_id = ? {habit_filter}
                ORDER BY completed_on DESC, created_at DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [row_to_dict(row) for row in rows]

    def completions_by_day(self, user_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT completed_on, COUNT(*) AS count, SUM(xp_awarded) AS xp
                FROM habit_completions
                WHERE user_id = ?
                GROUP BY completed_on
                ORDER BY completed_on
                """,
                (user_id,),
            ).fetchall()
        return [row_to_dict(row) for row in rows]

    def unlock_achievement(self, user_id, code, title, description):
        with get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO achievements (user_id, code, title, description)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, code, title, description),
            )

    def list_achievements(self, user_id):
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM achievements WHERE user_id = ? ORDER BY unlocked_at DESC",
                (user_id,),
            ).fetchall()
        return [row_to_dict(row) for row in rows]

    def get_notification_preferences(self, user_id):
        with get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO notification_preferences (user_id) VALUES (?)", (user_id,))
            return row_to_dict(
                conn.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,)).fetchone()
            )

    def update_notification_preferences(self, user_id, data):
        with get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO notification_preferences (user_id) VALUES (?)", (user_id,))
            conn.execute(
                """
                UPDATE notification_preferences
                SET habit_reminders = ?, inactivity_alerts = ?, weekly_summary = ?, monthly_summary = ?
                WHERE user_id = ?
                """,
                (
                    1 if data.get("habit_reminders") else 0,
                    1 if data.get("inactivity_alerts") else 0,
                    1 if data.get("weekly_summary") else 0,
                    1 if data.get("monthly_summary") else 0,
                    user_id,
                ),
            )
            return row_to_dict(
                conn.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,)).fetchone()
            )


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
