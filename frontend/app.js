const state = {
  user: JSON.parse(localStorage.getItem("growloopUser") || "null"),
  currentView: "habits",
  habits: [],
  notifiedReminderKeys: new Set(),
  reminderIntervalId: null,
};

const authPanel = document.querySelector("#authPanel");
const dashboard = document.querySelector("#dashboard");
const loginForm = document.querySelector("#loginForm");
const registerForm = document.querySelector("#registerForm");
const authMessage = document.querySelector("#authMessage");
const dashboardMessage = document.querySelector("#dashboardMessage");
const habitList = document.querySelector("#habitList");
const habitForm = document.querySelector("#habitForm");
const xpValue = document.querySelector("#xpValue");
const levelValue = document.querySelector("#levelValue");
const xpProgress = document.querySelector("#xpProgress");
const welcomeTitle = document.querySelector("#welcomeTitle");
const detailsPanel = document.querySelector("#detailsPanel");
const detailsContent = document.querySelector("#detailsContent");
const habitFormTitle = document.querySelector("#habitFormTitle");
const habitSubmitButton = document.querySelector("#habitSubmitButton");
const cancelEditButton = document.querySelector("#cancelEditButton");
const showPaused = document.querySelector("#showPaused");
const habitIdInput = document.querySelector("#habitId");

document.querySelector("#showLogin").addEventListener("click", () => switchAuthTab("login"));
document.querySelector("#showRegister").addEventListener("click", () => switchAuthTab("register"));
document.querySelector("#logoutButton").addEventListener("click", logout);
document.querySelector("#onboardingForm").addEventListener("submit", saveOnboarding);
document.querySelector("#settingsForm").addEventListener("submit", saveSettings);
document.querySelector("#refreshAnalytics").addEventListener("click", loadAnalytics);
document.querySelector("#refreshSmart").addEventListener("click", loadSmartCoach);
document.querySelector("#closeDetailsButton").addEventListener("click", () => detailsPanel.classList.add("hidden"));
cancelEditButton.addEventListener("click", resetHabitForm);
showPaused.addEventListener("change", loadHabits);
habitForm.addEventListener("submit", saveHabit);
loginForm.addEventListener("submit", login);
registerForm.addEventListener("submit", register);

document.querySelectorAll(".nav-button").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

function switchAuthTab(tab) {
  const isLogin = tab === "login";
  loginForm.classList.toggle("hidden", !isLogin);
  registerForm.classList.toggle("hidden", isLogin);
  document.querySelector("#showLogin").classList.toggle("active", isLogin);
  document.querySelector("#showRegister").classList.toggle("active", !isLogin);
  authMessage.textContent = "";
}

function switchView(view) {
  state.currentView = view;
  document.querySelectorAll(".view").forEach((section) => section.classList.add("hidden"));
  document.querySelector(`#${view}View`).classList.remove("hidden");
  document.querySelectorAll(".nav-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  dashboardMessage.textContent = "";
  if (view === "analytics") loadAnalytics();
  if (view === "achievements") loadAchievements();
  if (view === "smart") loadSmartCoach();
  if (view === "settings") loadSettings();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(state.user?.session_token ? { "Authorization": `Bearer ${state.user.session_token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

function formToJson(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function register(event) {
  event.preventDefault();
  try {
    await api("/api/register", {
      method: "POST",
      body: JSON.stringify(formToJson(registerForm)),
    });
    authMessage.textContent = "Registration successful. Please log in.";
    registerForm.reset();
    switchAuthTab("login");
  } catch (error) {
    authMessage.textContent = error.message;
  }
}

async function login(event) {
  event.preventDefault();
  try {
    const user = await api("/api/login", {
      method: "POST",
      body: JSON.stringify(formToJson(loginForm)),
    });
    state.user = user;
    localStorage.setItem("growloopUser", JSON.stringify(user));
    loginForm.reset();
    await showDashboard();
  } catch (error) {
    authMessage.textContent = error.message;
  }
}

async function saveOnboarding(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const result = await api("/api/onboarding", {
      method: "POST",
      body: JSON.stringify(formToJson(event.currentTarget)),
    });
    dashboardMessage.textContent = result.message;
    form.reset();
    switchView("smart");
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function saveHabit(event) {
  event.preventDefault();
  const data = formToJson(event.currentTarget);
  const id = data.id;
  delete data.id;
  try {
    if (id) {
      await api(`/api/habits/${id}`, { method: "PUT", body: JSON.stringify(data) });
      dashboardMessage.textContent = "Habit updated.";
    } else {
      await api("/api/habits", { method: "POST", body: JSON.stringify(data) });
      dashboardMessage.textContent = "Habit created.";
    }
    resetHabitForm();
    await loadHabits();
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function completeHabit(id) {
  try {
    const result = await api(`/api/habits/${id}/complete`, { method: "POST", body: "{}" });
    state.user.xp = result.xp;
    state.user.level = result.level;
    state.user.xp_progress = result.xp_progress;
    state.user.xp_to_next_level = result.xp_to_next_level;
    localStorage.setItem("growloopUser", JSON.stringify(state.user));
    updateProfile();
    dashboardMessage.textContent = "Habit completed. +10 XP";
    await loadHabits();
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function deleteHabit(id) {
  if (!confirm("Delete this habit?")) return;
  try {
    await api(`/api/habits/${id}`, { method: "DELETE" });
    dashboardMessage.textContent = "Habit deleted.";
    await loadHabits();
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function toggleHabit(id, isActive) {
  const action = isActive ? "pause" : "resume";
  try {
    await api(`/api/habits/${id}/${action}`, { method: "POST", body: "{}" });
    dashboardMessage.textContent = isActive ? "Habit paused." : "Habit resumed.";
    await loadHabits();
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function loadHabits() {
  const includeInactive = showPaused.checked ? "1" : "0";
  state.habits = await api(`/api/habits?include_inactive=${includeInactive}`);
  habitList.innerHTML = "";
  if (state.habits.length === 0) {
    habitList.innerHTML = '<p class="subtle">No habits yet. Add your first habit to start the loop.</p>';
    return;
  }
  for (const habit of state.habits) {
    const item = document.createElement("article");
    item.className = `habit-item ${habit.completed_today ? "completed" : ""} ${habit.is_active ? "" : "paused"}`;
    item.innerHTML = `
      <div>
        <h4>${escapeHtml(habit.name)}</h4>
        <div class="habit-meta">${escapeHtml(habit.category)} | ${escapeHtml(habit.frequency)} | ${escapeHtml(habit.difficulty)} | ${escapeHtml(habit.target_time)}</div>
        <div class="habit-meta">Streak: ${habit.streak} days | Completions: ${habit.completion_count}</div>
      </div>
      <div class="habit-actions">
        <button type="button" ${habit.completed_today || !habit.is_active ? "disabled" : ""} data-complete="${habit.id}">
          ${habit.completed_today ? "Done" : "Complete"}
        </button>
        <button class="ghost" type="button" data-details="${habit.id}">Details</button>
        <button class="ghost" type="button" data-edit="${habit.id}">Edit</button>
        <button class="ghost" type="button" data-toggle="${habit.id}">${habit.is_active ? "Pause" : "Resume"}</button>
        <button class="danger" type="button" data-delete="${habit.id}">Delete</button>
      </div>
    `;
    habitList.appendChild(item);
  }
}

function editHabit(id) {
  const habit = state.habits.find((item) => String(item.id) === String(id));
  if (!habit) return;
  habitIdInput.value = habit.id;
  habitForm.name.value = habit.name;
  habitForm.description.value = habit.description || "";
  habitForm.category.value = habit.category;
  habitForm.frequency.value = habit.frequency;
  habitForm.target_time.value = habit.target_time;
  habitForm.difficulty.value = habit.difficulty;
  habitForm.reminder.value = habit.reminder || "";
  habitFormTitle.textContent = "Edit Habit";
  habitSubmitButton.textContent = "Update habit";
  cancelEditButton.classList.remove("hidden");
  habitForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetHabitForm() {
  habitForm.reset();
  habitIdInput.value = "";
  habitFormTitle.textContent = "Add Habit";
  habitSubmitButton.textContent = "Save habit";
  cancelEditButton.classList.add("hidden");
}

async function showDetails(id) {
  try {
    const habit = await api(`/api/habits/${id}`);
    document.querySelector("#detailsTitle").textContent = habit.name;
    const history = habit.completion_history.length
      ? habit.completion_history.map((item) => `<li>${escapeHtml(item.completed_on)} - ${item.xp_awarded} XP</li>`).join("")
      : "<li>No completions yet.</li>";
    const suggestions = habit.improvement_suggestions.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    detailsContent.innerHTML = `
      <p>${escapeHtml(habit.description || "No description added.")}</p>
      <div class="details-grid">
        <span>Frequency: <strong>${escapeHtml(habit.frequency)}</strong></span>
        <span>Difficulty: <strong>${escapeHtml(habit.difficulty)}</strong></span>
        <span>Streak: <strong>${habit.streak}</strong></span>
        <span>Total completions: <strong>${habit.completion_count}</strong></span>
      </div>
      <h4>Completion History</h4>
      <ul>${history}</ul>
      <h4>Improvement Suggestions</h4>
      <ul>${suggestions}</ul>
    `;
    detailsPanel.classList.remove("hidden");
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function loadAnalytics() {
  const analytics = await api("/api/analytics");
  document.querySelector("#analyticsGrid").innerHTML = `
    ${metricCard("Active habits", analytics.active_habits)}
    ${metricCard("Paused habits", analytics.paused_habits)}
    ${metricCard("Completions", analytics.total_completions)}
    ${metricCard("XP earned", analytics.total_xp)}
    <article class="info-panel wide-panel"><h4>Best habit</h4><p>${escapeHtml(analytics.best_habit)}</p></article>
    <article class="info-panel wide-panel"><h4>Weekly reflection</h4><p>${escapeHtml(analytics.weekly_summary)}</p></article>
    <article class="info-panel wide-panel"><h4>Monthly summary</h4><p>${escapeHtml(analytics.monthly_summary)}</p></article>
  `;
}

async function loadAchievements() {
  const achievements = await api("/api/achievements");
  document.querySelector("#achievementList").innerHTML = achievements.map((item) => `
    <article class="achievement ${item.unlocked ? "unlocked" : ""}">
      <h4>${escapeHtml(item.title)}</h4>
      <p>${escapeHtml(item.description)}</p>
      <span>${item.unlocked ? `Unlocked ${escapeHtml(item.unlocked_at)}` : "Locked"}</span>
    </article>
  `).join("");
}

async function loadSmartCoach() {
  const data = await api("/api/recommendations");
  document.querySelector("#coachGrid").innerHTML = `
    <article class="info-panel"><h4>Burnout detection</h4><p>${escapeHtml(data.burnout_detection)}</p></article>
    <article class="info-panel"><h4>Habit load</h4><p>${escapeHtml(data.habit_load_recommendation)}</p></article>
  `;
  document.querySelector("#suggestionList").innerHTML = data.habit_suggestions.map((item) => `
    <article class="suggestion">
      <div>
        <h4>${escapeHtml(item.name)}</h4>
        <p>${escapeHtml(item.reason)}</p>
      </div>
      <button type="button" data-suggestion='${escapeAttribute(JSON.stringify(item))}'>Accept</button>
    </article>
  `).join("");
}

async function loadSettings() {
  const prefs = await api("/api/notification-preferences");
  const form = document.querySelector("#settingsForm");
  ["habit_reminders", "inactivity_alerts", "weekly_summary", "monthly_summary"].forEach((field) => {
    form[field].checked = Boolean(prefs[field]);
  });
}

async function saveSettings(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    habit_reminders: form.habit_reminders.checked,
    inactivity_alerts: form.inactivity_alerts.checked,
    weekly_summary: form.weekly_summary.checked,
    monthly_summary: form.monthly_summary.checked,
  };
  await api("/api/notification-preferences", { method: "PUT", body: JSON.stringify(payload) });
  dashboardMessage.textContent = "Notification preferences saved.";
}

async function acceptSuggestion(data) {
  const payload = { ...data, description: data.reason, reminder: "" };
  delete payload.reason;
  await api("/api/habits", { method: "POST", body: JSON.stringify(payload) });
  dashboardMessage.textContent = "Suggested habit added.";
  switchView("habits");
  await loadHabits();
}

function metricCard(label, value) {
  return `<article class="info-panel"><h4>${label}</h4><strong>${value}</strong></article>`;
}

function updateProfile() {
  welcomeTitle.textContent = `Welcome, ${state.user.username}`;
  xpValue.textContent = state.user.xp || 0;
  levelValue.textContent = state.user.level || 1;
  xpProgress.style.width = `${state.user.xp_progress || 0}%`;
}

async function showDashboard() {
  authPanel.classList.add("hidden");
  dashboard.classList.remove("hidden");
  const sessionToken = state.user?.session_token;
  state.user = await api("/api/profile");
  if (sessionToken) {
    state.user.session_token = sessionToken;
  }
  localStorage.setItem("growloopUser", JSON.stringify(state.user));
  updateProfile();
  dashboardMessage.textContent = "";
  switchView("habits");
  await loadHabits();
  await setupReminderNotifications();
}

async function logout() {
  try {
    await api("/api/logout", { method: "POST", body: "{}" });
  } catch (_error) {
    // The local logout should still work if the server session already expired.
  }
  state.user = null;
  localStorage.removeItem("growloopUser");
  dashboard.classList.add("hidden");
  authPanel.classList.remove("hidden");
}

async function setupReminderNotifications() {
  if (!state.user || state.reminderIntervalId) return;
  if (!("Notification" in window)) return;
  if (Notification.permission === "default") {
    await Notification.requestPermission();
  }
  state.reminderIntervalId = window.setInterval(checkDueReminders, 30000);
  await checkDueReminders();
}

async function checkDueReminders() {
  if (!state.user || Notification.permission !== "granted") return;
  let prefs;
  try {
    prefs = await api("/api/notification-preferences");
  } catch (_error) {
    return;
  }
  if (!prefs.habit_reminders) return;
  const now = new Date();
  const current = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  const today = now.toISOString().slice(0, 10);
  state.habits
    .filter((habit) => habit.is_active && habit.reminder === current && !habit.completed_today)
    .forEach((habit) => {
      const key = `${today}-${habit.id}-${current}`;
      if (state.notifiedReminderKeys.has(key)) return;
      state.notifiedReminderKeys.add(key);
      new Notification("GrowLoop habit reminder", {
        body: `Time for: ${habit.name}`,
      });
    });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}

habitList.addEventListener("click", (event) => {
  const completeId = event.target.dataset.complete;
  const deleteId = event.target.dataset.delete;
  const editId = event.target.dataset.edit;
  const detailsId = event.target.dataset.details;
  const toggleId = event.target.dataset.toggle;
  if (completeId) completeHabit(completeId);
  if (deleteId) deleteHabit(deleteId);
  if (editId) editHabit(editId);
  if (detailsId) showDetails(detailsId);
  if (toggleId) {
    const habit = state.habits.find((item) => String(item.id) === String(toggleId));
    if (habit) toggleHabit(toggleId, habit.is_active);
  }
});

document.querySelector("#suggestionList").addEventListener("click", (event) => {
  const suggestion = event.target.dataset.suggestion;
  if (suggestion) acceptSuggestion(JSON.parse(suggestion));
});

if (state.user) {
  showDashboard();
}
