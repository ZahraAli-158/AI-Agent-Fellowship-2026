window.toggleMemoryPin = async function (id) {
  const res = await fetch(`${window.DASH_CONFIG.base}/memory/${id}/pin`, { method: "POST" });
  const data = await res.json();
  const row = document.querySelector(`.memory-row[data-id="${id}"] .memory-content`);
  if (row) {
    const text = row.innerText.replace("📌 ", "");
    row.innerText = (data.is_pinned ? "📌 " : "") + text;
  }
};

window.deleteMemory = async function (id) {
  if (!confirm("Remove this memory item?")) return;
  await fetch(`${window.DASH_CONFIG.base}/memory/${id}/delete`, { method: "POST" });
  const row = document.querySelector(`.memory-row[data-id="${id}"]`);
  if (row) row.remove();
};

window.addMemory = function (event) {
  event.preventDefault();
  const input = document.getElementById("memory-input");
  const content = input.value.trim();
  if (!content) return false;

  const formData = new FormData();
  formData.append("content", content);
  fetch(`${window.DASH_CONFIG.base}/memory/add`, { method: "POST", body: formData }).then(() => {
    location.reload();
  });
  return false;
};
