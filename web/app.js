// Giao diện chat: gửi câu hỏi tới POST /api/chat và đọc câu trả lời dạng SSE.
// Hợp đồng API: docs/02-api-contract.md

const API = (window.CHATBOT_CONFIG && window.CHATBOT_CONFIG.API_BASE) || "";

const els = {
  chat: document.getElementById("chat"),
  empty: document.getElementById("empty"),
  messages: document.getElementById("messages"),
  form: document.getElementById("composer"),
  input: document.getElementById("input"),
  send: document.getElementById("send"),
  newChat: document.getElementById("new-chat"),
  tplUser: document.getElementById("tpl-user"),
  tplBot: document.getElementById("tpl-bot"),
};

// session_id giữ trong trình duyệt để backend giới hạn tần suất và gom log
function getSessionId() {
  try {
    let id = localStorage.getItem("chatbot-session");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("chatbot-session", id);
    }
    return id;
  } catch (_) {
    return crypto.randomUUID();
  }
}
const sessionId = getSessionId();
let history = []; // [{role, content}], chỉ gửi 6 lượt gần nhất
let busy = false;

// ---------- hiển thị ----------
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Biến [1], [2] thành link tới nguồn tương ứng
function renderAnswer(text, msgId, sourceCount) {
  return escapeHtml(text).replace(/\[(\d+)\]/g, (m, n) =>
    Number(n) >= 1 && Number(n) <= sourceCount
      ? `<a class="cite" href="#${msgId}-src-${n}">[${n}]</a>`
      : m
  );
}

function scrollToBottom() {
  els.chat.scrollTop = els.chat.scrollHeight;
}

function addUser(text) {
  const node = els.tplUser.content.firstElementChild.cloneNode(true);
  node.querySelector(".bubble").textContent = text;
  els.messages.appendChild(node);
}

function addBot() {
  const node = els.tplBot.content.firstElementChild.cloneNode(true);
  node.id = "m-" + Math.random().toString(36).slice(2, 8);
  els.messages.appendChild(node);
  return node;
}

function showSources(node, sources) {
  const list = node.querySelector(".sources");
  list.innerHTML = "";
  sources.forEach((s) => {
    const li = document.createElement("li");
    li.id = `${node.id}-src-${s.n}`;
    const title = escapeHtml(s.title + (s.section ? " – " + s.section : ""));
    const date = s.effective_date ? ` <small>(hiệu lực ${escapeHtml(s.effective_date)})</small>` : "";
    li.innerHTML = `<b>[${s.n}]</b>` +
      (s.url ? `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${title}</a>` : title) + date;
    list.appendChild(li);
  });
  list.hidden = sources.length === 0;
}

function showFeedback(node, answerId) {
  const box = node.querySelector(".feedback");
  box.hidden = false;
  box.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      box.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      try {
        await fetch(`${API}/api/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ answer_id: answerId, rating: Number(btn.dataset.rating) }),
        });
        box.querySelector("span").textContent = "Cảm ơn bạn đã phản hồi.";
      } catch (_) {
        box.querySelector("span").textContent = "Chưa gửi được phản hồi.";
      }
    });
  });
}

// ---------- đọc SSE từ fetch (EventSource không hỗ trợ POST) ----------
async function* readSSE(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      let event = "message", data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) yield { event, data: JSON.parse(data) };
    }
  }
}

// ---------- gửi câu hỏi ----------
async function ask(question) {
  if (busy || !question.trim()) return;
  busy = true;
  els.send.disabled = true;
  els.empty.hidden = true;

  addUser(question);
  const bot = addBot();
  const status = bot.querySelector(".status");
  const textEl = bot.querySelector(".text");
  scrollToBottom();

  let answer = "";
  let sources = [];

  try {
    const res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question, session_id: sessionId, history: history.slice(-6) }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || (res.status === 422 ? "Câu hỏi không hợp lệ (rỗng hoặc quá dài)." : `Lỗi ${res.status}`));
    }

    for await (const { event, data } of readSSE(res)) {
      if (event === "token") {
        status.textContent = "";
        answer += data.text;
        textEl.textContent = answer;
        scrollToBottom();
      } else if (event === "sources") {
        sources = data;
        textEl.innerHTML = renderAnswer(answer, bot.id, sources.length);
        showSources(bot, sources);
      } else if (event === "done") {
        showFeedback(bot, data.answer_id);
      } else if (event === "error") {
        throw new Error(data.message);
      }
    }

    history.push({ role: "user", content: question }, { role: "assistant", content: answer });
  } catch (e) {
    bot.classList.add("error");
    status.textContent = "";
    textEl.textContent = (e.message || "Không kết nối được máy chủ.") + " ";
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "ghost";
    retry.textContent = "Thử lại";
    retry.addEventListener("click", () => {
      bot.remove();
      els.messages.lastElementChild?.remove(); // bỏ câu hỏi cũ, hỏi lại
      ask(question);
    });
    textEl.appendChild(retry);
  } finally {
    busy = false;
    els.send.disabled = false;
    scrollToBottom();
  }
}

// ---------- sự kiện ----------
els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = els.input.value;
  els.input.value = "";
  els.input.style.height = "";
  ask(q);
});

els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    els.form.requestSubmit();
  }
});

els.input.addEventListener("input", () => {
  els.input.style.height = "auto";
  els.input.style.height = els.input.scrollHeight + "px";
});

document.querySelectorAll("#suggestions button").forEach((b) =>
  b.addEventListener("click", () => ask(b.textContent))
);

els.newChat.addEventListener("click", () => {
  history = [];
  els.messages.innerHTML = "";
  els.empty.hidden = false;
  els.input.focus();
});
