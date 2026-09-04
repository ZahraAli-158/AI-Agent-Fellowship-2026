(function () {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const messagesEl = document.getElementById("chat-messages");
  if (!form) return;

  function renderMarkdown(el, rawText) {
    if (window.marked && window.DOMPurify) {
      el.innerHTML = window.DOMPurify.sanitize(window.marked.parse(rawText || ""));
    } else {
      el.innerText = rawText || "";
    }
  }

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

  function appendMessage(role, content, toolCalls) {
    const emptyState = messagesEl.querySelector(".chat-empty");
    if (emptyState) emptyState.remove();

    const row = document.createElement("div");
    row.className = "msg-row msg-" + role;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.innerText = role === "user" ? window.AGENT_CHAT_CONFIG.userInitial : window.AGENT_CHAT_CONFIG.assistantInitial;

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";

    if (toolCalls && toolCalls.length) {
      const logWrap = document.createElement("div");
      logWrap.className = "tool-call-log";
      toolCalls.forEach((tc) => {
        const chip = document.createElement("span");
        chip.className = "tool-call-chip";
        chip.innerText = "🔧 " + tc.tool;
        logWrap.appendChild(chip);
      });
      bubble.appendChild(logWrap);
    }

    const text = document.createElement("div");
    text.className = "msg-text";
    renderMarkdown(text, content);
    bubble.appendChild(text);

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

    appendMessage("user", text, null);
    input.value = "";
    input.style.height = "auto";

    const thinkingBubble = appendMessage("assistant", "_Working on it..._", null);

    const formData = new FormData();
    formData.append("message", text);

    try {
      const res = await fetch(window.AGENT_CHAT_CONFIG.sendUrl, { method: "POST", body: formData });
      const data = await res.json();
      thinkingBubble.parentElement.remove();

      if (data.error) {
        appendMessage("assistant", "**Error:** " + data.error, null);
        return;
      }
      appendMessage("assistant", data.assistant_message.content, data.assistant_message.tool_calls);

      const titleDisplay = document.getElementById("convo-title-display");
      if (titleDisplay && data.conversation_title) titleDisplay.innerText = data.conversation_title;

      // The agent may have created/updated/completed/deleted tasks via its
      // tools this turn — refresh the live tasks panel to reflect that.
      if (data.assistant_message.tool_calls && data.assistant_message.tool_calls.length && window.refreshAgentTasks) {
        window.refreshAgentTasks();
      }
    } catch (err) {
      const textEl = thinkingBubble.querySelector(".msg-text");
      if (textEl) textEl.innerText = "Network error — please try again.";
    }
  });

  // ---------- Voice input (reuses the same pattern as the workspace chat) ----------
  (function setupVoiceInput() {
    const micBtn = document.getElementById("mic-btn");
    if (!micBtn) return;

    const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionImpl) {
      micBtn.title = "Voice input needs Chrome or Edge (not supported in this browser)";
      micBtn.disabled = true;
      micBtn.style.opacity = "0.4";
      return;
    }
    const isSecureEnough = window.isSecureContext || ["localhost", "127.0.0.1"].includes(window.location.hostname);
    if (!isSecureEnough) {
      micBtn.title = "Voice input needs HTTPS (or localhost) to access the microphone";
      micBtn.disabled = true;
      micBtn.style.opacity = "0.4";
      return;
    }

    const recognition = new SpeechRecognitionImpl();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    let listening = false;

    recognition.onstart = () => { listening = true; micBtn.classList.add("recording"); };
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      input.value = (input.value ? input.value + " " : "") + transcript;
      input.dispatchEvent(new Event("input"));
    };
    recognition.onend = () => { listening = false; micBtn.classList.remove("recording"); };
    recognition.onerror = (event) => {
      listening = false;
      micBtn.classList.remove("recording");
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        alert("Microphone access was blocked. Allow it for this site in your browser's address-bar settings.");
      }
    };

    micBtn.addEventListener("click", () => {
      if (listening) {
        try { recognition.stop(); } catch (e) {}
        return;
      }
      try { recognition.start(); } catch (e) { micBtn.classList.remove("recording"); }
    });
  })();
})();
