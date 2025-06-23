document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".wpchatbot-form");
  const input = form?.querySelector(".wpchatbot-input");
  const messages = document.querySelector(".wpchatbot-messages");

  // Auto-grow behavior for the input field
  input?.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = input.scrollHeight + "px";
  });

  console.log("Form:", form);
  console.log("Input:", input);
  console.log("Messages:", messages);

  if (!form || !input || !messages) {
    console.error("Chatbot elements not found!");
    return;
  }

  /* ------------------------------------------------------------------ */
  /*  Utilities                                                         */
  /* ------------------------------------------------------------------ */
  let sessionUuid = null;
  const userId = form.dataset.userId;
  const initialMessage = form.dataset.initialMessage;

  const escapeHtml = (str) =>
    typeof str === "string"
      ? str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;")
      : "";

  /* ------------------------------------------------------------------ */
  /*  Input: submit on Enter (without closing modal)                    */
  /* ------------------------------------------------------------------ */
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      console.log("Enter detected → submitting form");
      form.dispatchEvent(new Event("submit", { bubbles: true }));
    }
  });

  /* ------------------------------------------------------------------ */
  /*  Form submit → call WP proxy endpoint                              */
  /* ------------------------------------------------------------------ */
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = input.value.trim();
    console.log("Submitting message:", msg);
    if (!msg) return;

    appendMessage(msg, "user");
    input.value = "";
    input.disabled = true;

    try {
      const endpoint = form.dataset.endpoint;
      console.log("Sending fetch to:", endpoint);
      const intUserId = parseInt(userId, 10);
      console.log("Request body:", JSON.stringify({ user_id: intUserId, session_uuid: sessionUuid, message: msg }));

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: intUserId, session_uuid: sessionUuid, message: msg })
      });

      console.log("Fetch response object:", res);
      console.log("Fetch response status:", res.status);
      let data;
      try {
        data = await res.json();
        console.log("Fetch response data:", data);
      } catch (jsonErr) {
        const text = await res.text();
        console.error("Failed to parse JSON. Response text:", text);
        throw new Error("❗ Failed to parse backend response as JSON. See console for details.");
      }

      if (!res.ok || !data.answer) {
        throw new Error(data.message || "Backend error.");
      }

      if (data.session_uuid) {
        sessionUuid = data.session_uuid;
        console.log("Session UUID updated:", sessionUuid);
      }

      appendMessage(data.answer, "bot");
    } catch (err) {
      console.error("Chat API Error:", err);
      appendMessage(`❗ ${err.message}", "bot-error`);
    } finally {
      input.disabled = false;
      input.focus();
    }
  });

  // Show initial message if set (display as bot message only)
  if (initialMessage) {
    // Conform to PlainText model as JSON string
    appendMessage([{ type: "plaintext", text: initialMessage }], "bot");
  }

  /* ------------------------------------------------------------------ */
  /*  Parse backend components → HTML                                   */
  /* ------------------------------------------------------------------ */
  function parseToComponents(arr) {
    console.log("Parsing answer components:", arr);

    if (!Array.isArray(arr)) {
      return `<p class="chatbot-plaintext">Unexpected response format.</p>`;
    }

    let html = "";
    let group = [];

    arr.forEach((comp, idx) => {
      const isCard = ["producercomponent", "productcomponent"].includes(comp.type);
      const nextIsCard = arr[idx + 1] && ["producercomponent", "productcomponent"].includes(arr[idx + 1].type);

      if (isCard) {
        group.push(comp);
        if (!nextIsCard) {
          html += '<div class="chatbot-horizontal-scroll">';
          group.forEach(item => {
            console.log(item.img_url)
            html += `
              <div class="chatbot-component-card chatbot-${item.type === "producercomponent" ? "producer" : "product"}">
                ${item.img_url ? `<img src="${escapeHtml(item.img_url)}" alt="${escapeHtml(item.title)}" style="max-width:250px;">` : ""}
                <h3>${escapeHtml(item.title)}</h3>
                <p>${escapeHtml(item.display_content)}</p>
                ${item.link
                ? `<a href="${escapeHtml(item.link)}" target="_blank" class="chatbot-button">
                       View ${item.type === "producercomponent" ? "Producer" : "Product"}
                     </a>`
                : ""}
              </div>`;
          });
          html += "</div>";
          group = [];
        }
        return; // skip default switch for card components
      }

      switch (comp.type) {
        case "plaintext":
          html += `<p class="chatbot-plaintext">${escapeHtml(comp.text)}</p>`;
          break;

        case "optionquestion":
          html += `<div class="chatbot-optionquestion">
                     <p class="chatbot-optionquestion-text">${escapeHtml(comp.display_content)}</p>
                     <div class="chatbot-optionquestion-options">`;
          comp.options?.forEach(opt => {
            html += `<button class="btn--primary btn--s chatbot-option-button"
                              data-next-query="${escapeHtml(opt.next_user_query)}">
                        ${escapeHtml(opt.display_content)}
                     </button>`;
          });
          html += "</div></div>";
          break;

        default:
          html += `<p class="chatbot-plaintext"><i>[Unsupported type: ${escapeHtml(comp.type)}]</i></p>`;
      }
    });

    return html;
  }

  /* ------------------------------------------------------------------ */
  /*  Append a message bubble                                           */
  /* ------------------------------------------------------------------ */
  function appendMessage(content, role) {
    console.log("Appending message. Role:", role, "Content:", content);

    const div = document.createElement("div");
    div.className = `wpchatbot-${role === "bot-error" ? "bot" : role}-message`;

    if (role === "bot") {
      div.innerHTML = parseToComponents(content);

      div.querySelectorAll(".chatbot-option-button").forEach(btn => {
        btn.addEventListener("click", () => {
          console.log("Option clicked:", btn.dataset.nextQuery);
          input.value = btn.dataset.nextQuery || "";
          form.dispatchEvent(new Event("submit", { bubbles: true }));
        });
      });
    } else if (role === "bot-error") {
      div.innerHTML = `<p style="color:red;">${escapeHtml(content)}</p>`;
    } else {
      div.textContent = content;
    }

    messages.appendChild(div);
    // messages.scrollTop = messages.scrollHeight; // Disabled auto-scroll to bottom
  }
});
