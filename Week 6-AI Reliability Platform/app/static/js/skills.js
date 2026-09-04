(function () {
  let currentSkillId = null;
  let currentExecution = null; // holds the last-opened run-detail payload

  function renderMarkdown(el, rawText) {
    if (window.marked && window.DOMPurify) {
      el.innerHTML = window.DOMPurify.sanitize(window.marked.parse(rawText || ""));
    } else {
      el.innerText = rawText || "";
    }
  }

  window.openSkillModal = function (skillId, name, icon) {
    currentSkillId = skillId;
    document.getElementById("skill-modal-title").innerText = `${icon} ${name}`;
    document.getElementById("skill-input").value = "";
    document.getElementById("skill-output").innerHTML = "";
    openModal("skill-modal");
  };

  window.runSkill = async function () {
    const inputText = document.getElementById("skill-input").value.trim();
    if (!inputText || !currentSkillId) return;
    const btn = document.getElementById("skill-run-btn");
    const outputEl = document.getElementById("skill-output");
    btn.innerText = "Running...";
    btn.disabled = true;
    outputEl.innerHTML = '<p class="muted">Generating...</p>';

    const formData = new FormData();
    formData.append("input_text", inputText);

    try {
      const res = await fetch(`${window.SKILL_CONFIG.runUrlBase}/${currentSkillId}/run`, { method: "POST", body: formData });
      const data = await res.json();
      if (data.error) {
        outputEl.innerHTML = "";
        outputEl.innerText = data.error;
      } else {
        renderMarkdown(outputEl, data.output);
      }
    } catch (e) {
      outputEl.innerHTML = "";
      outputEl.innerText = "Network error — please try again.";
    } finally {
      btn.innerText = "Run skill";
      btn.disabled = false;
    }
  };

  // ---------- Reopen / rerun / continue-in-chat for a past run ----------
  window.openRunModal = async function (executionId) {
    const titleEl = document.getElementById("run-detail-title");
    const metaEl = document.getElementById("run-detail-meta");
    const inputEl = document.getElementById("run-detail-input");
    const outputEl = document.getElementById("run-detail-output");

    titleEl.innerText = "Loading...";
    metaEl.innerText = "";
    inputEl.innerText = "";
    outputEl.innerHTML = "";
    openModal("run-detail-modal");

    try {
      const res = await fetch(`${window.SKILL_CONFIG.runUrlBase}/execution/${executionId}`);
      if (!res.ok) throw new Error("not found");
      const data = await res.json();
      currentExecution = data;

      titleEl.innerText = `${data.skill_icon} ${data.skill_name}`;
      metaEl.innerText = `${data.created_at} · ${data.duration_ms}ms`;
      inputEl.innerText = data.input_text;
      renderMarkdown(outputEl, data.output_text);
    } catch (e) {
      titleEl.innerText = "Couldn't load this run";
      metaEl.innerText = "";
    }
  };

  window.rerunFromDetail = function () {
    if (!currentExecution) return;
    closeModal("run-detail-modal");
    window.openSkillModal(currentExecution.skill_id, currentExecution.skill_name, currentExecution.skill_icon);
    document.getElementById("skill-input").value = currentExecution.input_text;
  };

  window.continueInChat = async function () {
    if (!currentExecution) return;
    const btn = document.getElementById("run-detail-chat-btn");
    btn.innerText = "Opening chat...";
    btn.disabled = true;
    try {
      const res = await fetch(`${window.SKILL_CONFIG.runUrlBase}/execution/${currentExecution.id}/continue-chat`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.redirect) {
        window.location.href = data.redirect;
      }
    } catch (e) {
      btn.innerText = "💬 Continue in Chat";
      btn.disabled = false;
      alert("Couldn't start a chat from this run — please try again.");
    }
  };
})();
