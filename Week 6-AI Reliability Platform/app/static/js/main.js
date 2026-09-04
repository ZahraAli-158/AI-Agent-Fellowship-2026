// ---------- Modal helpers ----------
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("open");
}
function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove("open");
}
document.addEventListener("click", (e) => {
  if (e.target.classList && e.target.classList.contains("modal")) {
    e.target.classList.remove("open");
  }
});

// ---------- Tabs ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    const panel = document.getElementById("tab-" + tab);
    if (panel) panel.classList.add("active");
  });
});

// ---------- Theme toggle ----------
(function () {
  const root = document.documentElement;
  const saved = localStorage.getItem("ai_platform_theme");
  if (saved) root.setAttribute("data-theme", saved);

  const btn = document.getElementById("theme-toggle");
  const icon = document.getElementById("theme-icon");
  function syncIcon() {
    if (!icon) return;
    icon.innerText = root.getAttribute("data-theme") === "light" ? "☀️" : "🌙";
  }
  syncIcon();
  if (btn) {
    btn.addEventListener("click", () => {
      const current = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      root.setAttribute("data-theme", current);
      localStorage.setItem("ai_platform_theme", current);
      syncIcon();
    });
  }
})();

// ---------- Flash auto-dismiss ----------
setTimeout(() => {
  const stack = document.getElementById("flash-stack");
  if (stack) stack.querySelectorAll(".flash").forEach((f) => f.remove());
}, 6000);
