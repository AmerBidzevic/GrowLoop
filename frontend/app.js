const state = {
  user: JSON.parse(localStorage.getItem("growloopUser") || "null"),
};

const authPanel = document.querySelector("#authPanel");
const dashboard = document.querySelector("#dashboard");
const loginForm = document.querySelector("#loginForm");
const registerForm = document.querySelector("#registerForm");
const authMessage = document.querySelector("#authMessage");
const dashboardMessage = document.querySelector("#dashboardMessage");
const habitList = document.querySelector("#habitList");
const xpValue = document.querySelector("#xpValue");
const welcomeTitle = document.querySelector("#welcomeTitle");

document.querySelector("#showLogin").addEventListener("click", () => switchAuthTab("login"));
document.querySelector("#showRegister").addEventListener("click", () => switchAuthTab("register"));
document.querySelector("#logoutButton").addEventListener("click", logout);
document.querySelector("#onboardingForm").addEventListener("submit", saveOnboarding);
document.querySelector("#habitForm").addEventListener("submit", createHabit);
loginForm.addEventListener("submit", login);
registerForm.addEventListener("submit", register);

function switchAuthTab(tab) {
  const isLogin = tab === "login";
  loginForm.classList.toggle("hidden", !isLogin);
  registerForm.classList.toggle("hidden", isLogin);
  document.querySelector("#showLogin").classList.toggle("active", isLogin);
  document.querySelector("#showRegister").classList.toggle("active", !isLogin);
  authMessage.textContent = "";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(state.user ? { "X-User-Id": state.user.id } : {}),
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
    showDashboard();
  } catch (error) {
    authMessage.textContent = error.message;
  }
}

async function saveOnboarding(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api("/api/onboarding", {
      method: "POST",
      body: JSON.stringify(formToJson(event.currentTarget)),
    });
    dashboardMessage.textContent = "Onboarding saved. Suggested habits are ready to create.";
    form.reset();
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function createHabit(event) {
  event.preventDefault();
  try {
    await api("/api/habits", {
      method: "POST",
      body: JSON.stringify(formToJson(event.currentTarget)),
    });
    event.currentTarget.reset();
    dashboardMessage.textContent = "Habit created.";
    await loadHabits();
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function completeHabit(id) {
  try {
    const result = await api(`/api/habits/${id}/complete`, { method: "POST", body: "{}" });
    state.user.xp = result.xp;
    localStorage.setItem("growloopUser", JSON.stringify(state.user));
    updateProfile();
    dashboardMessage.textContent = "Habit completed. +10 XP";
    await loadHabits();
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function deleteHabit(id) {
  if (!confirm("Delete this habit?")) {
    return;
  }
  try {
    await api(`/api/habits/${id}`, { method: "DELETE" });
    dashboardMessage.textContent = "Habit deleted.";
    await loadHabits();
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function loadHabits() {
  const habits = await api("/api/habits");
  habitList.innerHTML = "";
  if (habits.length === 0) {
    habitList.innerHTML = '<p class="subtle">No habits yet. Add your first habit to start the loop.</p>';
    return;
  }
  for (const habit of habits) {
    const item = document.createElement("article");
    item.className = `habit-item ${habit.completed_today ? "completed" : ""}`;
    item.innerHTML = `
      <div>
        <h4>${escapeHtml(habit.name)}</h4>
        <div class="habit-meta">${escapeHtml(habit.category)} · ${escapeHtml(habit.frequency)} · ${escapeHtml(habit.difficulty)} · ${escapeHtml(habit.target_time)}</div>
      </div>
      <div class="habit-actions">
        <button type="button" ${habit.completed_today ? "disabled" : ""} data-complete="${habit.id}">
          ${habit.completed_today ? "Done" : "Complete"}
        </button>
        <button class="ghost" type="button" data-delete="${habit.id}">Delete</button>
      </div>
    `;
    habitList.appendChild(item);
  }
}

function updateProfile() {
  welcomeTitle.textContent = `Welcome, ${state.user.username}`;
  xpValue.textContent = state.user.xp;
}

async function showDashboard() {
  authPanel.classList.add("hidden");
  dashboard.classList.remove("hidden");
  updateProfile();
  dashboardMessage.textContent = "";
  await loadHabits();
}

function logout() {
  state.user = null;
  localStorage.removeItem("growloopUser");
  dashboard.classList.add("hidden");
  authPanel.classList.remove("hidden");
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

habitList.addEventListener("click", (event) => {
  const completeId = event.target.dataset.complete;
  const deleteId = event.target.dataset.delete;
  if (completeId) {
    completeHabit(completeId);
  }
  if (deleteId) {
    deleteHabit(deleteId);
  }
});

if (state.user) {
  showDashboard();
}

