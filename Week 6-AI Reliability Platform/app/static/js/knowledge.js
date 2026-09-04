(function () {
  const searchInput = document.getElementById("kb-search");
  const resultsEl = document.getElementById("kb-search-results");
  let timer;

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(timer);
      const q = searchInput.value.trim();
      timer = setTimeout(async () => {
        if (!q) { resultsEl.innerHTML = ""; return; }
        const res = await fetch(window.KB_CONFIG.searchUrl + "?q=" + encodeURIComponent(q));
        const data = await res.json();
        resultsEl.innerHTML = "";
        if (!data.results.length) {
          resultsEl.innerHTML = '<p class="muted">No matches found.</p>';
          return;
        }
        data.results.forEach((r) => {
          const div = document.createElement("div");
          div.className = "kb-result";
          div.innerHTML = `<div class="kb-result-head"><span>📄 ${r.document} · chunk ${r.chunk_index}</span><span>${Math.round(r.score * 100)}% match</span></div><div>${r.snippet}</div>`;
          resultsEl.appendChild(div);
        });
      }, 300);
    });
  }

  let currentDocId = null;

  window.openAskModal = function (docId, filename) {
    currentDocId = docId;
    document.getElementById("ask-modal-title").innerText = "Ask: " + filename;
    document.getElementById("ask-input").value = "";
    document.getElementById("ask-answer").innerText = "";
    openModal("ask-modal");
  };

  window.submitAsk = async function () {
    const question = document.getElementById("ask-input").value.trim();
    if (!question || !currentDocId) return;
    const btn = document.getElementById("ask-submit-btn");
    const answerEl = document.getElementById("ask-answer");
    btn.innerText = "Thinking...";
    btn.disabled = true;

    const formData = new FormData();
    formData.append("question", question);

    try {
      const res = await fetch(`${window.KB_CONFIG.askUrlBase}/${currentDocId}/ask`, { method: "POST", body: formData });
      const data = await res.json();
      answerEl.innerText = data.answer || data.error || "No answer available.";
    } catch (e) {
      answerEl.innerText = "Network error — please try again.";
    } finally {
      btn.innerText = "Ask";
      btn.disabled = false;
    }
  };
})();
