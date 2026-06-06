from datetime import date, timedelta

from database import hash_password, verify_password
from repository import GrowLoopRepository


ACHIEVEMENT_RULES = [
    ("FIRST_STEP", "First Step", "Complete your first habit.", lambda stats: stats["total_completions"] >= 1),
    ("FIVE_WINS", "Five Wins", "Complete five habits.", lambda stats: stats["total_completions"] >= 5),
    ("TEN_WINS", "Ten Wins", "Complete ten habits.", lambda stats: stats["total_completions"] >= 10),
    ("LEVEL_2", "Level 2", "Reach level 2.", lambda stats: stats["level"] >= 2),
]


class AuthService:
    def __init__(self, repo=None):
        self.repo = repo or GrowLoopRepository()

    def register(self, data):
        password_hash, password_salt = hash_password(data["password"])
        user_id = self.repo.create_user(data["username"], data["email"], password_hash, password_salt)
        return {"id": user_id, "message": "Registration successful"}

    def login(self, email, password):
        user = self.repo.find_user_by_email(email)
        if not user or not verify_password(password, user["password_hash"], user["password_salt"]):
            return None
        profile = self.repo.get_user(user["id"])
        return enrich_profile(profile)


class HabitService:
    def __init__(self, repo=None):
        self.repo = repo or GrowLoopRepository()

    def list_habits(self, user_id, include_inactive=False):
        return [self.enrich_habit(user_id, habit) for habit in self.repo.list_habits(user_id, include_inactive)]

    def get_habit_details(self, user_id, habit_id):
        habit = self.repo.get_habit(user_id, habit_id)
        if not habit:
            return None
        habit = self.enrich_habit(user_id, habit)
        habit["completion_history"] = self.repo.list_completions(user_id, habit_id, 30)
        habit["improvement_suggestions"] = RecommendationEngine().improve_habit(habit)
        return habit

    def create_habit(self, user_id, data):
        return self.repo.create_habit(user_id, data)

    def update_habit(self, user_id, habit_id, data):
        return self.repo.update_habit(user_id, habit_id, data)

    def delete_habit(self, user_id, habit_id):
        return self.repo.delete_habit(user_id, habit_id)

    def set_active(self, user_id, habit_id, is_active):
        return self.repo.set_habit_active(user_id, habit_id, is_active)

    def complete_habit(self, user_id, habit_id):
        if not self.repo.get_habit(user_id, habit_id):
            return None
        user = self.repo.complete_habit(user_id, habit_id)
        AchievementService(self.repo).evaluate(user_id)
        return enrich_profile({"xp": user["xp"]})

    def enrich_habit(self, user_id, habit):
        completions = self.repo.list_completions(user_id, habit["id"], 60)
        habit["streak"] = calculate_streak([item["completed_on"] for item in completions])
        habit["completed_today"] = bool(habit["completed_today"])
        habit["is_active"] = bool(habit["is_active"])
        return habit


class AnalyticsService:
    def __init__(self, repo=None):
        self.repo = repo or GrowLoopRepository()

    def dashboard(self, user_id):
        habits = HabitService(self.repo).list_habits(user_id, include_inactive=True)
        completions = self.repo.list_completions(user_id, limit=500)
        active_habits = [habit for habit in habits if habit["is_active"]]
        total_completions = len(completions)
        best_habit = max(habits, key=lambda item: item["completion_count"], default=None)
        completion_days = self.repo.completions_by_day(user_id)
        return {
            "active_habits": len(active_habits),
            "paused_habits": len(habits) - len(active_habits),
            "total_completions": total_completions,
            "total_xp": total_completions * 10,
            "best_habit": best_habit["name"] if best_habit else "No data yet",
            "daily_activity": completion_days[-14:],
            "weekly_summary": self.summary("weekly", habits, completions),
            "monthly_summary": self.summary("monthly", habits, completions),
        }

    def summary(self, period, habits, completions):
        days = 7 if period == "weekly" else 30
        since = date.today() - timedelta(days=days - 1)
        recent = [item for item in completions if date.fromisoformat(item["completed_on"]) >= since]
        best = max(habits, key=lambda item: item["completion_count"], default=None)
        if not recent:
            return f"No {period} completions yet. Start with one easy habit today."
        return (
            f"{period.title()} summary: {len(recent)} completions, {len(recent) * 10} XP earned. "
            f"Best habit: {best['name'] if best else 'not available'}."
        )


class AchievementService:
    def __init__(self, repo=None):
        self.repo = repo or GrowLoopRepository()

    def evaluate(self, user_id):
        profile = enrich_profile(self.repo.get_user(user_id))
        completions = self.repo.list_completions(user_id, limit=1000)
        stats = {
            "level": profile["level"],
            "total_completions": len(completions),
        }
        for code, title, description, rule in ACHIEVEMENT_RULES:
            if rule(stats):
                self.repo.unlock_achievement(user_id, code, title, description)

    def list_with_locked(self, user_id):
        self.evaluate(user_id)
        unlocked = {achievement["code"]: achievement for achievement in self.repo.list_achievements(user_id)}
        result = []
        for code, title, description, _rule in ACHIEVEMENT_RULES:
            item = unlocked.get(code)
            result.append(
                {
                    "code": code,
                    "title": title,
                    "description": description,
                    "unlocked": item is not None,
                    "unlocked_at": item["unlocked_at"] if item else "",
                }
            )
        return result


class RecommendationEngine:
    """Strategy Pattern: smart guidance is split into small recommendation strategies."""

    def suggestions(self, onboarding):
        goal = (onboarding or {}).get("goals", "Productivity")
        schedule = (onboarding or {}).get("schedule", "Morning focused")
        library = {
            "Health": ["Drink water", "Walk for 15 minutes", "Stretch"],
            "Learning": ["Read 20 pages", "Practice notes", "Watch one lesson"],
            "Productivity": ["Plan tomorrow", "Clear inbox", "Deep work block"],
        }
        names = library.get(goal, library["Productivity"])
        return [
            {
                "name": name,
                "category": goal,
                "frequency": "Daily",
                "target_time": "08:00" if "Morning" in schedule else "18:00",
                "difficulty": "Easy",
                "reason": f"Recommended for your {goal.lower()} goal.",
            }
            for name in names
        ]

    def burnout(self, habits, completions):
        active_count = len([habit for habit in habits if habit["is_active"]])
        if active_count >= 6:
            return "High habit load detected. Pause one or two habits to protect consistency."
        if active_count >= 4 and len(completions) < active_count:
            return "Your habit load may be too high for the current completion pace."
        return "Habit load looks manageable."

    def adaptive_difficulty(self, habit):
        count = habit.get("completion_count", 0)
        difficulty = habit.get("difficulty", "Easy")
        if count >= 10 and difficulty != "Hard":
            return "Consider increasing difficulty because this habit is becoming consistent."
        if count == 0 and difficulty == "Hard":
            return "Consider lowering difficulty to make the habit easier to start."
        return "Current difficulty looks reasonable."

    def improve_habit(self, habit):
        return [
            self.adaptive_difficulty(habit),
            "Keep the target time close to an existing routine.",
            "Use a short description so the next action is obvious.",
        ]

    def dashboard(self, onboarding, habits, completions):
        return {
            "habit_suggestions": self.suggestions(onboarding),
            "burnout_detection": self.burnout(habits, completions),
            "habit_load_recommendation": self.burnout(habits, completions),
        }


def enrich_profile(profile):
    if not profile:
        return None
    xp = int(profile.get("xp", 0))
    level = xp // 100 + 1
    profile["level"] = level
    profile["xp_to_next_level"] = 100 - (xp % 100)
    profile["xp_progress"] = xp % 100
    return profile


def calculate_streak(completed_dates):
    completed = {date.fromisoformat(item) for item in completed_dates}
    streak = 0
    cursor = date.today()
    while cursor in completed:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
