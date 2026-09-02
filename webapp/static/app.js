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

// Confirms the page is actually running current code, not a cached build -
// fetched fresh (never cached, see server.py) so it's always the truth even
// if app.js itself somehow got served stale.
fetch("/api/version")
  .then((r) => r.json())
  .then((d) => { document.getElementById("versionTag").textContent = d.version; })
  .catch(() => {});

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

// Renders the ```chart fenced JSON blocks the personality prompt emits when
// asked for a chart/graph, by handing a plain Chart.js config to QuickChart
// (https://quickchart.io - free, no key, GET a PNG back) instead of drawing
// bars ourselves. Same categorical hues as before; no plotting dependency
// to install, and the same config shape will work for a Discord embed later.
const CHART_COLORS = ["#3987e5", "#d95926", "#199e70", "#c98500"];

function chartLegend(names) {
  if (names.length < 2) return "";
  const items = names
    .map((name, i) => `<span class="chart-legend-item"><i class="chart-swatch s${i % 4}"></i>${escapeHtml(String(name))}</span>`)
    .join("");
  return `<div class="chart-legend">${items}</div>`;
}

function chartAxis(unitTitle) {
  return {
    ticks: { color: "#ececec" },
    grid: { color: "rgba(255,255,255,0.08)" },
    title: unitTitle ? { display: true, text: String(unitTitle), color: "#ececec" } : undefined,
  };
}

function quickChartImg(config, { width = 480, height = 280, alt = "chart" } = {}) {
  // version=4: QuickChart defaults to Chart.js v2, which ignores this
  // config's v3/v4-style options (plugins.legend/title, scales.x/y) and
  // falls back to its own default legend instead.
  const url =
    `https://quickchart.io/chart?version=4&backgroundColor=transparent&width=${width}&height=${height}` +
    `&c=${encodeURIComponent(JSON.stringify(config))}`;
  return `<img class="chart-img" src="${url}" alt="${escapeHtml(alt)}" loading="lazy">`;
}

function renderChart(data) {
  if (data.type === "bar" && Array.isArray(data.categories)) {
    const seriesList = Array.isArray(data.series) ? data.series : [];
    const config = {
      type: "bar",
      data: {
        labels: data.categories,
        datasets: seriesList.map((s, i) => ({
          label: s.name || `Series ${i + 1}`,
          data: (s.values || []).map((v) => Number(v) || 0),
          backgroundColor: CHART_COLORS[i % CHART_COLORS.length],
        })),
      },
      options: {
        plugins: {
          legend: { display: seriesList.length > 1, labels: { color: "#ececec" } },
          title: data.title ? { display: true, text: String(data.title), color: "#ececec" } : undefined,
          datalabels: { anchor: "end", align: "end", color: "#ececec" },
        },
        layout: { padding: { top: 28 } },
        scales: { x: chartAxis(null), y: chartAxis(data.unit) },
      },
    };
    return `<div class="chart">${quickChartImg(config, { width: 520, alt: data.title })}</div>`;
  }

  // Different metrics rarely share a scale (points vs. sacks), so a
  // "comparison" is small multiples - one mini chart per row, all sharing
  // one color-to-name legend instead of repeating it on every chart.
  if (data.type === "comparison" && Array.isArray(data.rows)) {
    const series = (Array.isArray(data.series) ? data.series : []).map(String);
    const cells = data.rows
      .map((row) => {
        const values = (Array.isArray(row.values) ? row.values : []).map((v) => Number(v) || 0);
        const config = {
          type: "bar",
          data: {
            labels: series,
            datasets: [{
              data: values,
              backgroundColor: values.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]),
            }],
          },
          options: {
            plugins: {
              legend: { display: false },
              title: { display: true, text: String(row.label ?? ""), color: "#ececec" },
              datalabels: { anchor: "end", align: "end", color: "#ececec" },
            },
            layout: { padding: { top: 28 } },
            scales: { x: chartAxis(null), y: chartAxis(row.unit) },
          },
        };
        return `<div class="chart-cell">${quickChartImg(config, { width: 260, height: 200, alt: row.label })}</div>`;
      })
      .join("");
    const title = data.title ? `<div class="chart-title">${escapeHtml(String(data.title))}</div>` : "";
    return `<div class="chart">${title}${chartLegend(series)}<div class="chart-grid">${cells}</div></div>`;
  }

  return `<pre class="chart-raw">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
}

// Splits ```chart fenced JSON out of the reply and renders the rest as
// markdown, so a chart can be requested alongside normal prose framing.
function renderMessage(text) {
  const fenceRe = /```chart\s*\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let out = "";
  let match;
  while ((match = fenceRe.exec(text))) {
    out += renderMarkdown(text.slice(lastIndex, match.index));
    try {
      out += renderChart(JSON.parse(match[1]));
    } catch (err) {
      out += `<pre class="chart-raw">${escapeHtml(match[1].trim())}</pre>`;
    }
    lastIndex = fenceRe.lastIndex;
  }
  out += renderMarkdown(text.slice(lastIndex));
  return out;
}

function fmtArgs(v) {
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

// Short, fixed one-liners on what each node actually does - shown next to
// its label so the trace reads as "step + purpose" without needing a
// separate legend or a more visual layout.
const NODE_PURPOSE = {
  supervisor: "reads the question, decides which data categories to pull",
  run_category: "calls that category's tools to gather data",
  personality: "writes the final reply from everything gathered above",
};

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
      if (NODE_PURPOSE[evt.node]) detail = NODE_PURPOSE[evt.node];
      break;
    case "node_end":
      label = `■ ${evt.node}${evt.category ? ":" + evt.category : ""} — ${evt.duration_ms}ms`;
      // Reasoning first (the "why"), then what it decided, then the outcome.
      if (evt.reasoning) {
        detail = `reasoning: ${evt.reasoning}`;
      }
      if (evt.categories) {
        const list = evt.categories.length
          ? "categories chosen: " + evt.categories.join(", ")
          : "categories chosen: (none - answering from chat alone)";
        detail = (detail ? detail + "\n" : "") + list;
      }
      if (evt.tool_rounds !== undefined) {
        detail = (detail ? detail + "\n" : "") + `tool rounds used: ${evt.tool_rounds}`;
      }
      if (evt.text) {
        detail = (detail ? detail + "\n\nfinal reply:\n" : "") + evt.text;
      }
      break;
    case "tool_call":
      label = `→ round ${evt.round}: ${evt.category}.${evt.name}`;
      detail = "args: " + fmtArgs(evt.args);
      break;
    case "tool_result":
      label = `← round ${evt.round}: ${evt.category}.${evt.name || ""}` +
        (evt.duration_ms !== undefined ? ` — ${evt.duration_ms}ms` : "");
      detail = evt.result + (evt.truncated ? "\n…(truncated for trace display)" : "");
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

// One divider per user message, so the trace reads as separate turns
// instead of one continuous stream of same-looking rows.
function addTraceTurnDivider(message) {
  traceEl.querySelector(".trace-empty")?.remove();
  const div = document.createElement("div");
  div.className = "trace-turn";
  const short = message.length > 70 ? message.slice(0, 70) + "…" : message;
  div.textContent = `— "${short}" —`;
  traceEl.appendChild(div);
  traceEl.scrollTop = traceEl.scrollHeight;
}

async function send(message) {
  sendBtn.disabled = true;
  addMessage("user", message);
  addTraceTurnDivider(message);
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
          botDiv.innerHTML = renderMessage(botText);
          chatEl.scrollTop = chatEl.scrollHeight;
        } else if (evt.type === "done") {
          botDiv.innerHTML = renderMessage(evt.text);
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

document.getElementById("toggleLegend").addEventListener("click", () => {
  document.getElementById("traceLegend").hidden = !document.getElementById("traceLegend").hidden;
});

traceEl.innerHTML = '<div class="trace-empty">No activity yet.</div>';
input.focus();
