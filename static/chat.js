/* global sendMessage, deleteDocument are referenced from chat.html inline handlers */

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIcon(filename) {
  const ext = filename.split(".").pop().toLowerCase();
  return (
    {
      pdf: "📄",
      docx: "📝", doc: "📝",
      xlsx: "📊", xls: "📊",
      pptx: "📋", ppt: "📋",
      png: "🖼", jpg: "🖼", jpeg: "🖼",
      gif: "🖼", bmp: "🖼", tiff: "🖼", tif: "🖼", webp: "🖼",
    }[ext] || "📎"
  );
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function showStatus(msg, type /* "loading" | "success" | "error" */) {
  const el = document.getElementById("uploadStatus");
  el.className = `upload-status ${type}`;
  el.textContent = msg;
  el.classList.remove("hidden");
  if (type !== "loading") {
    setTimeout(() => el.classList.add("hidden"), 4500);
  }
}

// ── Document list ─────────────────────────────────────────────────────────────

async function loadDocuments() {
  try {
    const res = await fetch("/api/documents");
    const data = await res.json();
    const list = document.getElementById("docList");
    const countEl = document.getElementById("docCount");

    list.innerHTML = "";
    countEl.textContent = data.documents.length;

    data.documents.forEach((doc) => {
      const li = document.createElement("li");
      li.className = "doc-item";

      const icon = document.createElement("span");
      icon.className = "doc-icon";
      icon.textContent = fileIcon(doc.filename);

      const name = document.createElement("span");
      name.className = "doc-name";
      name.title = doc.filename;
      name.textContent = doc.filename;

      const size = document.createElement("span");
      size.className = "doc-size";
      size.textContent = formatSize(doc.size);

      const delBtn = document.createElement("button");
      delBtn.className = "doc-delete";
      delBtn.title = "Remove";
      delBtn.textContent = "✕";
      delBtn.addEventListener("click", () => deleteDocument(doc.filename));

      li.append(icon, name, size, delBtn);
      list.appendChild(li);
    });
  } catch (err) {
    console.error("Failed to load documents:", err);
  }
}

// ── Upload ────────────────────────────────────────────────────────────────────

async function uploadFiles(files) {
  if (!files || files.length === 0) return;

  showStatus(`Uploading ${files.length} file(s)…`, "loading");

  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  try {
    const res = await fetch("/api/documents/upload", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (data.errors && data.errors.length > 0) {
      showStatus(`⚠ ${data.errors.join("; ")}`, "error");
    } else if (data.uploaded && data.uploaded.length > 0) {
      showStatus(
        `✓ ${data.uploaded.length} document(s) added to knowledge base.`,
        "success"
      );
    } else {
      showStatus("No files were processed.", "error");
    }

    loadDocuments();
  } catch (err) {
    showStatus(`Upload failed: ${err.message}`, "error");
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────

async function deleteDocument(filename) {
  try {
    await fetch(`/api/documents/${encodeURIComponent(filename)}`, {
      method: "DELETE",
    });
    loadDocuments();
  } catch (err) {
    console.error("Delete failed:", err);
  }
}

// ── Chat messages ─────────────────────────────────────────────────────────────

function addMessage(role, text, sources = []) {
  const container = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = `message ${role}`;

  let html = `<div class="message-bubble">${escapeHtml(text)}</div>`;

  if (sources.length > 0) {
    const tags = sources
      .map((s) => `<span class="source-tag">📎 ${escapeHtml(s)}</span>`)
      .join("");
    html += `<div class="message-sources">${tags}</div>`;
  }

  div.innerHTML = html;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function addTypingIndicator() {
  const container = document.getElementById("messages");
  const div = document.createElement("div");
  div.id = "typingIndicator";
  div.className = "message assistant typing-indicator";
  div.innerHTML = `
    <div class="message-bubble">
      <div class="dot"></div><div class="dot"></div><div class="dot"></div>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typingIndicator");
  if (el) el.remove();
}

// ── Send message ──────────────────────────────────────────────────────────────

async function sendMessage() {
  const input = document.getElementById("questionInput");
  const question = input.value.trim();
  if (!question) return;

  input.value = "";
  input.style.height = "auto";

  const sendBtn = document.getElementById("sendBtn");
  sendBtn.disabled = true;

  addMessage("user", question);
  addTypingIndicator();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    removeTypingIndicator();

    if (!res.ok) {
      addMessage("assistant", `Error: ${data.error || "Unknown error"}`);
    } else {
      addMessage("assistant", data.answer, data.sources || []);
    }
  } catch (err) {
    removeTypingIndicator();
    addMessage("assistant", `Connection error: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

// ── Drag-and-drop ─────────────────────────────────────────────────────────────

const uploadZone = document.getElementById("uploadZone");

uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("drag-over");
});

uploadZone.addEventListener("dragleave", () =>
  uploadZone.classList.remove("drag-over")
);

uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("drag-over");
  uploadFiles(e.dataTransfer.files);
});

document.getElementById("fileInput").addEventListener("change", (e) => {
  uploadFiles(e.target.files);
  e.target.value = "";
});

// ── Keyboard shortcuts ────────────────────────────────────────────────────────

document.getElementById("questionInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Auto-resize textarea
document.getElementById("questionInput").addEventListener("input", function () {
  this.style.height = "auto";
  this.style.height = Math.min(this.scrollHeight, 140) + "px";
});

// ── Init ──────────────────────────────────────────────────────────────────────
loadDocuments();
