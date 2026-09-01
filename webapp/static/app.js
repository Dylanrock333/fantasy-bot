const chatEl = document.getElementById("chat");
const traceEl = document.getElementById("trace");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = form.querySelector("button");

let sessionId = localStorage.getItem("sessionId");
if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem("sessionId", sessionId);
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
  return div;
}

// Small hand-rolled renderer for the subset of markdown the personality
// prompt actually produces (bold, inline code, headings, bullet/numbered
// lists) - avoids pulling in a dependency for a locally-hosted tool.
function renderMarkdown(text) {
  function inline(s) {
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, "$1<em>$2</em>");
    return s;
  }

  const lines = escapeHtml(text).split("\n");
  const out = [];
  let listType = null;
  let para = [];

  const flushPara = () => {
    if (para.length) {
      out.push(`<p>${para.join("<br>")}</p>`);
      para = [];
    }
  };
  const closeList = () => {
    if (listType) {
      out.push(`</${listType}>`);
      listType = null;
    }
  };

  for (const raw of lines) {
    const line = raw.trim();
    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    const bullet = /^[-*]\s+(.*)$/.exec(line);
    const numbered = /^\d+\.\s+(.*)$/.exec(line);

    if (!line) {
      flushPara();
      closeList();
    } else if (heading) {
      flushPara();
      closeList();
      const level = Math.min(heading[1].length + 2, 4);
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
    } else if (bullet) {
      flushPara();
      if (listType !== "ul") {
        closeList();
        out.push("<ul>");
        listType = "ul";
      }
      out.push(`<li>${inline(bullet[1])}</li>`);
    } else if (numbered) {
      flushPara();
      if (listType !== "ol") {
        closeList();
        out.push("<ol>");
        listType = "ol";
      }
      out.push(`<li>${inline(numbered[1])}</li>`);
    } else {
      closeList();
      para.push(inline(line));
    }
  }
  flushPara();
  closeList();
  return out.join("\n");
}

function fmtArgs(v) {
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

function addTraceEvent(evt) {
  traceEl.querySelector(".trace-empty")?.remove();

  const div = document.createElement("div");
  div.className = `trace-event trace-${evt.type}`;
  const time = new Date(evt.ts * 1000).toLocaleTimeString();

  let label = evt.type;
  let detail = "";

  switch (evt.type) {
    case "node_start":
      label = `▶ ${evt.node}${evt.category ? ":" + evt.category : ""}`;
      break;
    case "node_end":
      label = `■ ${evt.node}${evt.category ? ":" + evt.category : ""} — ${evt.duration_ms}ms`;
      if (evt.categories) {
        detail = evt.categories.length
          ? "categories: " + evt.categories.join(", ")
          : "categories: (none)";
      }
      if (evt.tool_rounds !== undefined) {
        detail = (detail ? detail + "\n" : "") + `tool rounds: ${evt.tool_rounds}`;
      }
      if (evt.text) {
        detail = (detail ? detail + "\n\n" : "") + evt.text;
      }
      break;
    case "tool_call":
      label = `→ ${evt.category}.${evt.name}`;
      detail = fmtArgs(evt.args);
      break;
    case "tool_result":
      label = `← ${evt.category}.${evt.name || ""}`;
      detail = evt.result;
      break;
    case "node_warning":
      label = `⚠ ${evt.node}`;
      detail = evt.message;
      break;
    case "error":
      label = "⚠ error";
      detail = evt.message;
      break;
  }

  div.innerHTML =
    `<span class="trace-time">${time}</span><span class="trace-label">${escapeHtml(label)}</span>` +
    (detail ? `<pre class="trace-detail">${escapeHtml(detail)}</pre>` : "");

  traceEl.appendChild(div);
  traceEl.scrollTop = traceEl.scrollHeight;
}

async function send(message) {
  sendBtn.disabled = true;
  addMessage("user", message);
  input.value = "";

  const botDiv = addMessage("bot", "");
  botDiv.classList.add("pending");
  let botText = "";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop();

      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        const evt = JSON.parse(part.slice(6));

        if (evt.type === "token") {
          botText += evt.text;
          botDiv.innerHTML = renderMarkdown(botText);
          chatEl.scrollTop = chatEl.scrollHeight;
        } else if (evt.type === "done") {
          botDiv.innerHTML = renderMarkdown(evt.text);
          botDiv.classList.remove("pending");
        } else if (evt.type === "error") {
          botDiv.textContent = `error: ${evt.message}`;
          botDiv.classList.remove("pending");
          botDiv.classList.add("error");
          addTraceEvent(evt);
        } else {
          addTraceEvent(evt);
        }
      }
    }
  } catch (err) {
    botDiv.textContent = `network error: ${err}`;
    botDiv.classList.remove("pending");
    botDiv.classList.add("error");
  } finally {
    botDiv.classList.remove("pending");
    sendBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  send(message);
});

document.getElementById("newChat").addEventListener("click", async () => {
  await fetch("/api/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  chatEl.innerHTML = "";
  traceEl.innerHTML = '<div class="trace-empty">No activity yet.</div>';
});

document.getElementById("clearTrace").addEventListener("click", () => {
  traceEl.innerHTML = '<div class="trace-empty">No activity yet.</div>';
});

const tracePane = document.querySelector(".trace-pane");
const toggleTraceBtn = document.getElementById("toggleTrace");

function applyTraceCollapsed(collapsed) {
  tracePane.classList.toggle("collapsed", collapsed);
  toggleTraceBtn.textContent = collapsed ? "Show trace" : "Hide trace";
}

const storedTraceCollapsed = localStorage.getItem("traceCollapsed");
const isMobile = window.matchMedia("(max-width: 768px)").matches;
let traceCollapsed = storedTraceCollapsed === null ? isMobile : storedTraceCollapsed === "true";
applyTraceCollapsed(traceCollapsed);

toggleTraceBtn.addEventListener("click", () => {
  traceCollapsed = !traceCollapsed;
  localStorage.setItem("traceCollapsed", String(traceCollapsed));
  applyTraceCollapsed(traceCollapsed);
});

traceEl.innerHTML = '<div class="trace-empty">No activity yet.</div>';
input.focus();
