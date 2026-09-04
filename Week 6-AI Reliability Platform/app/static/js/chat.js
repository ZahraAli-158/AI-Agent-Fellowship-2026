(function () {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const messagesEl = document.getElementById("chat-messages");
  const useKnowledge = document.getElementById("use-knowledge");
  if (!form) return;

  // ---------- Markdown rendering (headings, bullets, tables, code, etc.) ----------
  function renderMarkdown(el, rawText) {
    if (window.marked && window.DOMPurify) {
      const html = window.DOMPurify.sanitize(window.marked.parse(rawText || ""));
      el.innerHTML = html;
    } else {
      // Fallback if the CDN scripts didn't load (e.g. offline dev environment)
      el.innerText = rawText;
    }
  }

  // Re-render any server-rendered messages already in the DOM as markdown,
  // since Jinja outputs them as plain escaped text.
  document.querySelectorAll(".msg-text[data-raw]").forEach((el) => {
    renderMarkdown(el, el.dataset.raw);
  });

  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function buildActionsBar(role, messageId) {
    const wrap = document.createElement("div");
    wrap.className = "msg-actions";

    const pinBtn = document.createElement("button");
    pinBtn.className = "msg-action-btn";
    pinBtn.title = "Pin message";
    pinBtn.innerText = "📍";
    pinBtn.onclick = () => window.toggleMessagePin(messageId, pinBtn);
    wrap.appendChild(pinBtn);

    if (role === "assistant") {
      const speakBtn = document.createElement("button");
      speakBtn.className = "msg-action-btn";
      speakBtn.title = "Read aloud";
      speakBtn.innerText = "🔊";
      speakBtn.onclick = () => window.speakMessage(speakBtn);
      wrap.appendChild(speakBtn);
    }
    return wrap;
  }

  function appendMessage(role, content, citations, messageId) {
    const emptyState = messagesEl.querySelector(".chat-empty");
    if (emptyState) emptyState.remove();

    const row = document.createElement("div");
    row.className = "msg-row msg-" + role;
    if (messageId) row.dataset.id = messageId;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.innerText = role === "user" ? window.CHAT_CONFIG.userInitial : window.CHAT_CONFIG.assistantInitial;

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    const text = document.createElement("div");
    text.className = "msg-text";
    renderMarkdown(text, content);
    bubble.appendChild(text);

    if (citations && citations.length) {
      const citeWrap = document.createElement("div");
      citeWrap.className = "msg-citations";
      citations.forEach((c) => {
        const chip = document.createElement("span");
        chip.className = "citation-chip";
        chip.title = c.snippet;
        chip.innerText = `📄 ${c.document} · chunk ${c.chunk_index} (${Math.round(c.score * 100)}%)`;
        citeWrap.appendChild(chip);
      });
      bubble.appendChild(citeWrap);
    }

    if (messageId) {
      bubble.appendChild(buildActionsBar(role, messageId));
    }

    row.appendChild(avatar);
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    scrollToBottom();
    return bubble;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    appendMessage("user", text, null, null);
    input.value = "";
    input.style.height = "auto";

    const thinkingBubble = appendMessage("assistant", "_Thinking..._", null, null);
    thinkingBubble.classList.add("thinking");

    const formData = new FormData();
    formData.append("message", text);
    if (useKnowledge.checked) formData.append("use_knowledge", "on");

    try {
      const res = await fetch(window.CHAT_CONFIG.sendUrl, { method: "POST", body: formData });
      const data = await res.json();
      thinkingBubble.parentElement.remove();

      if (data.error) {
        appendMessage("assistant", "**Error:** " + data.error, null, null);
        return;
      }
      appendMessage(
        "assistant",
        data.assistant_message.content,
        data.assistant_message.citations,
        data.assistant_message.id
      );

      const titleDisplay = document.getElementById("convo-title-display");
      if (titleDisplay && data.conversation_title) titleDisplay.innerText = data.conversation_title;
    } catch (err) {
      const textEl = thinkingBubble.querySelector(".msg-text");
      if (textEl) textEl.innerText = "Network error — please try again.";
    }
  });

  // ---------- Conversation search ----------
  const searchInput = document.getElementById("convo-search");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const q = searchInput.value.trim().toLowerCase();
      const list = document.getElementById("convo-mini-list");
      list.querySelectorAll(".convo-mini").forEach((el) => {
        el.style.display = !q || el.innerText.toLowerCase().includes(q) ? "" : "none";
      });
    });
  }

  window.togglePin = async function (conversationId) {
    const res = await fetch(`${window.CHAT_CONFIG.pinUrlBase}/${conversationId}/pin`, { method: "POST" });
    const data = await res.json();
    const btn = document.getElementById("pin-btn");
    if (btn) btn.innerText = data.is_pinned ? "📌" : "📍";
  };

  // ---------- Advanced feature: Pinned Messages ----------
  window.toggleMessagePin = async function (messageId, btnEl) {
    const res = await fetch(`${window.CHAT_CONFIG.pinUrlBase}/message/${messageId}/pin`, { method: "POST" });
    const data = await res.json();
    if (btnEl) btnEl.innerText = data.is_pinned ? "📌" : "📍";
  };

  // ---------- Advanced feature: Speech Output (text-to-speech) ----------
  // Tracks whichever speak button is currently active so a second click on
  // the SAME button stops it immediately, instead of waiting for the whole
  // answer to finish.
  let currentSpeakBtn = null;

  function resetSpeakBtn(btnEl) {
    btnEl.innerText = "🔊";
    btnEl.title = "Read aloud";
  }

  window.speakMessage = function (btnEl) {
    if (!("speechSynthesis" in window)) {
      alert("Speech output isn't supported in this browser.");
      return;
    }

    // Clicking the button that's currently speaking = stop it right away.
    if (currentSpeakBtn === btnEl) {
      window.speechSynthesis.cancel();
      resetSpeakBtn(btnEl);
      currentSpeakBtn = null;
      return;
    }

    // Something else was speaking — stop it and reset its icon first.
    window.speechSynthesis.cancel();
    if (currentSpeakBtn) resetSpeakBtn(currentSpeakBtn);

    const bubble = btnEl.closest(".msg-bubble");
    const textEl = bubble.querySelector(".msg-text");
    const plainText = textEl ? textEl.innerText : "";
    if (!plainText.trim()) return;

    const utterance = new SpeechSynthesisUtterance(plainText);
    utterance.rate = 1;

    currentSpeakBtn = btnEl;
    btnEl.innerText = "⏹️";
    btnEl.title = "Stop reading";

    utterance.onend = () => {
      if (currentSpeakBtn === btnEl) {
        resetSpeakBtn(btnEl);
        currentSpeakBtn = null;
      }
    };
    utterance.onerror = utterance.onend;

    // Some browsers need a fresh call stack after cancel() before speak()
    // reliably starts the next utterance.
    setTimeout(() => window.speechSynthesis.speak(utterance), 0);
  };

  // ---------- Advanced feature: Voice Input (speech-to-text) ----------
  (function setupVoiceInput() {
    const micBtn = document.getElementById("mic-btn");
    if (!micBtn) return;

    const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionImpl) {
      micBtn.title = "Voice input needs Chrome or Edge (not supported in this browser)";
      micBtn.disabled = true;
      micBtn.style.opacity = "0.4";
      console.warn("Voice input: window.SpeechRecognition / webkitSpeechRecognition not found in this browser.");
      return;
    }

    // Voice input requires a secure context (https, or localhost/127.0.0.1).
    // On any other plain-http host the browser silently refuses to start.
    const isSecureEnough = window.isSecureContext || ["localhost", "127.0.0.1"].includes(window.location.hostname);
    if (!isSecureEnough) {
      micBtn.title = "Voice input needs HTTPS (or localhost) to access the microphone";
      micBtn.disabled = true;
      micBtn.style.opacity = "0.4";
      console.warn("Voice input: insecure context — browsers block microphone access outside https/localhost.");
      return;
    }

    const recognition = new SpeechRecognitionImpl();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    let listening = false;

    recognition.onstart = () => {
      listening = true;
      micBtn.classList.add("recording");
    };
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      input.value = (input.value ? input.value + " " : "") + transcript;
      input.dispatchEvent(new Event("input"));
    };
    recognition.onend = () => {
      listening = false;
      micBtn.classList.remove("recording");
    };
    recognition.onerror = (event) => {
      listening = false;
      micBtn.classList.remove("recording");
      console.warn("Voice input error:", event.error);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        alert("Microphone access was blocked. Click the 🔒/site-info icon in the address bar and allow the microphone for this site, then try again.");
      } else if (event.error === "no-speech") {
        // Nothing said — no need to alarm the user, just reset quietly.
      } else {
        alert("Voice input error: " + event.error);
      }
    };

    micBtn.addEventListener("click", () => {
      if (listening) {
        try { recognition.stop(); } catch (e) { /* already stopped */ }
        return;
      }
      try {
        recognition.start();
      } catch (e) {
        // Most commonly thrown when start() is called again before the
        // previous session fully ended — safe to ignore visually.
        console.warn("Voice input start() failed:", e);
        micBtn.classList.remove("recording");
      }
    });
  })();

  // ---------- Advanced feature: Tagging ----------
  window.saveTags = async function () {
    const tagsInput = document.getElementById("tags-input");
    const formData = new FormData();
    formData.append("tags", tagsInput.value.trim());

    const res = await fetch(window.CHAT_CONFIG.tagsUrl, { method: "POST", body: formData });
    const data = await res.json();

    const row = document.getElementById("chat-tags-row");
    const addBtn = row.querySelector(".icon-btn.tiny");
    row.querySelectorAll(".tag-chip").forEach((el) => el.remove());
    (data.tags || "").split(",").filter((t) => t.trim()).forEach((t) => {
      const chip = document.createElement("span");
      chip.className = "tag-chip";
      chip.innerText = "🏷️ " + t.trim();
      row.insertBefore(chip, addBtn);
    });

    if (typeof closeModal === "function") closeModal("tags-modal");
  };
})();
