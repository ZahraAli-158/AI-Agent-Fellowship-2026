function renderTaskRow(task) {
  const row = document.createElement("div");
  row.className = "task-row" + (task.status === "completed" ? " task-done" : "");
  row.dataset.id = task.id;

  const due = task.due_date ? `<span>📅 ${task.due_date}</span>` : "";
  const desc = task.description ? `<div class="task-desc">${task.description}</div>` : "";

  row.innerHTML = `
    <button class="task-check" onclick="toggleAgentTask(${task.id})" title="Mark complete">${task.status === "completed" ? "✅" : "⬜"}</button>
    <div class="task-body">
      <div class="task-title"></div>
      ${desc}
      <div class="task-meta">
        <span class="task-status-chip task-status-${task.status}">${task.status.replace("_", " ")}</span>
        ${due}
      </div>
    </div>
    <button class="icon-btn danger" onclick="deleteAgentTask(${task.id})" title="Delete">🗑️</button>
  `;
  row.querySelector(".task-title").innerText = task.title; // safe text insertion
  return row;
}

window.addAgentTask = function (event) {
  event.preventDefault();
  const titleInput = document.getElementById("task-title-input");
  const dueInput = document.getElementById("task-due-input");
  const title = titleInput.value.trim();
  if (!title) return false;

  const formData = new FormData();
  formData.append("title", title);
  if (dueInput.value) formData.append("due_date", dueInput.value);

  fetch(`${window.AGENT_TASKS_CONFIG.base}/create`, { method: "POST", body: formData })
    .then((res) => res.json())
    .then((data) => {
      if (!data.task) return;
      const list = document.getElementById("agent-task-list");
      const emptyMsg = document.getElementById("agent-task-empty");
      if (emptyMsg) emptyMsg.remove();
      list.prepend(renderTaskRow(data.task));
      titleInput.value = "";
      dueInput.value = "";
    });
  return false;
};

window.toggleAgentTask = function (taskId) {
  fetch(`${window.AGENT_TASKS_CONFIG.base}/${taskId}/complete`, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      if (!data.task) return;
      const row = document.querySelector(`.task-row[data-id="${taskId}"]`);
      if (row) row.replaceWith(renderTaskRow(data.task));
    });
};

window.deleteAgentTask = function (taskId) {
  fetch(`${window.AGENT_TASKS_CONFIG.base}/${taskId}/delete`, { method: "POST" })
    .then(() => {
      const row = document.querySelector(`.task-row[data-id="${taskId}"]`);
      if (row) row.remove();
    });
};

// Full refresh from the server — used after an agent turn, since the
// agent's own tools (create_task/complete_task/delete_task) can change
// tasks without going through the buttons above.
window.refreshAgentTasks = function () {
  if (!window.AGENT_TASKS_CONFIG) return;
  fetch(`${window.AGENT_TASKS_CONFIG.base}.json`)
    .then((res) => res.json())
    .then((data) => {
      const list = document.getElementById("agent-task-list");
      if (!list) return;
      list.innerHTML = "";
      if (!data.tasks.length) {
        const p = document.createElement("p");
        p.className = "muted";
        p.id = "agent-task-empty";
        p.innerText = "No tasks yet — add one above, or ask the agent to create some from your meeting notes.";
        list.appendChild(p);
        return;
      }
      data.tasks.forEach((t) => list.appendChild(renderTaskRow(t)));
    });
};
