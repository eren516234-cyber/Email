import os
import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
ALLOWED_EXT = os.getenv("ALLOWED_EXT", "png,jpg,jpeg,gif,txt,pdf,docx,zip,mp4,mp3").split(",")
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # default 16 MB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.secret_key = os.getenv("FLASK_SECRET", "dev_secret_change_me")
DB_PATH = os.getenv("DB_PATH", "chat.db")

# --- DB helpers ---
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

db = get_db()
def init_db():
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        text TEXT,
        file_name TEXT,
        file_path TEXT,
        created_at TEXT
    )
    """)
    db.commit()

init_db()

# --- Helpers ---
def allowed_file(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXT

# --- Routes ---
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Local Chat & File Share — Made by Shourya</title>
  <style>
    :root{
      --bg:#0f1724;
      --card:#0b1220;
      --muted:#9aa4b2;
      --accent:#7c5cff;
      --me:#1f2937;
      --you:#0b1220;
      --bubble-me:#7c5cff;
      --bubble-you:#111827;
      --text-light:#e6eef8;
      --maxw:900px;
    }
    html,body{height:100%; margin:0; font-family:Inter, Roboto, Arial, sans-serif; background:linear-gradient(180deg,#071126 0%, #0b1320 100%); color:var(--text-light);}
    .wrap{max-width:var(--maxw); margin:0 auto; height:100vh; display:flex; flex-direction:column; padding:12px;}
    header{display:flex; align-items:center; gap:12px; padding:10px 8px; border-radius:12px; background:rgba(255,255,255,0.02); box-shadow:0 6px 18px rgba(2,6,23,0.6); }
    .logo{width:44px; height:44px; border-radius:10px; background:linear-gradient(135deg,#7c5cff,#5eead4); display:flex; align-items:center; justify-content:center; font-weight:700; color:#081023;}
    header h1{font-size:16px; margin:0;}
    header p{margin:0; font-size:12px; color:var(--muted);}
    main{flex:1; margin-top:12px; display:flex; flex-direction:column; gap:10px;}
    #chat{flex:1; overflow:auto; padding:16px; border-radius:12px; background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);}
    .msg-row{display:flex; gap:8px; margin-bottom:10px; align-items:flex-end;}
    .msg-row.me{justify-content:flex-end;}
    .bubble{max-width:78%; padding:10px 12px; border-radius:12px; box-shadow:0 4px 14px rgba(2,6,23,0.6); color:var(--text-light); font-size:14px; line-height:1.3;}
    .bubble .meta{display:block; font-size:11px; color:var(--muted); margin-bottom:6px;}
    .bubble.you{background:var(--bubble-you);}
    .bubble.me{background:linear-gradient(90deg, #6f56ff, #7c5cff); text-align:right;}
    .file-link{display:inline-block; margin-top:6px; padding:6px 8px; background:rgba(255,255,255,0.03); border-radius:8px; font-size:13px; color:var(--text-light); text-decoration:none;}
    .footer{display:flex; gap:8px; align-items:center; padding:10px; background:transparent; position:sticky; bottom:0; margin-top:8px;}
    input[type="text"], textarea{background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.03); color:var(--text-light); padding:10px; border-radius:8px; outline:none; width:100%;}
    #controls{display:flex; gap:8px; align-items:center; width:100%;}
    #fileInput{display:none;}
    .btn{padding:10px 12px; border-radius:10px; background:var(--accent); color:#021024; border:none; cursor:pointer; font-weight:600;}
    .small-btn{padding:8px 10px; border-radius:8px; background:rgba(255,255,255,0.03); color:var(--text-light); border:1px solid rgba(255,255,255,0.03); cursor:pointer;}
    .brand{font-size:11px; color:var(--muted); text-align:center; margin-top:8px;}
    .top-row{display:flex; gap:8px; align-items:center; justify-content:space-between;}
    @media (max-width:520px){
      .bubble{max-width:92%;}
      header h1{font-size:14px;}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="logo">SA</div>
      <div style="flex:1">
        <h1>Local Chat & File Share</h1>
        <p>Share messages & files on the same Wi-Fi — Made by Shourya</p>
      </div>
      <div style="text-align:right">
        <div style="font-size:12px; color:var(--muted)">Status</div>
        <div id="status" style="font-weight:700; color:#7ee7b8; font-size:12px">Online</div>
      </div>
    </header>

    <main>
      <div class="top-row">
        <div style="display:flex; gap:8px; align-items:center;">
          <input id="username" type="text" placeholder="Your name (save automatically)" style="width:220px;" />
          <button id="saveName" class="small-btn">Save</button>
        </div>
        <div style="font-size:12px; color:var(--muted)">Open in Chrome: <strong id="open-url">127.0.0.1:5000</strong></div>
      </div>

      <div id="chat" aria-live="polite"></div>

      <div class="footer">
        <form id="sendForm" enctype="multipart/form-data" style="display:flex; gap:8px; width:100%;">
          <label for="fileInput" class="small-btn" title="Attach file">📎</label>
          <input type="file" id="fileInput" name="file" />
          <textarea id="msgbox" name="text" rows="1" placeholder="Type a message..." style="resize:none;"></textarea>
          <button type="submit" class="btn">Send</button>
          <button type="button" id="clearBtn" class="small-btn" title="Clear chat">Clear</button>
        </form>
      </div>

      <div class="brand">Made by Shourya · Local & private on your device</div>
    </main>
  </div>

<script>
const chatEl = document.getElementById("chat");
const form = document.getElementById("sendForm");
const usernameInput = document.getElementById("username");
const fileInput = document.getElementById("fileInput");
const msgbox = document.getElementById("msgbox");
const clearBtn = document.getElementById("clearBtn");
const saveNameBtn = document.getElementById("saveName");
const openUrlEl = document.getElementById("open-url");
const statusEl = document.getElementById("status");

let lastId = 0;
const POLL_MS = 1500;

// Show the URL (detect if not on 127.0.0.1)
(function setOpenUrl() {
  try {
    const host = location.hostname || "127.0.0.1";
    const port = location.port || "5000";
    openUrlEl.textContent = host + ":" + port;
  } catch (e) {}
})();

function saveNameToStorage() {
  const v = usernameInput.value.trim();
  if (v) localStorage.setItem("local_chat_name", v);
  else localStorage.removeItem("local_chat_name");
}
function loadNameFromStorage() {
  const v = localStorage.getItem("local_chat_name") || "";
  usernameInput.value = v;
}
loadNameFromStorage();

saveNameBtn.addEventListener("click", () => {
  saveNameToStorage();
  saveNameBtn.textContent = "Saved ✓";
  setTimeout(()=> saveNameBtn.textContent = "Save", 1200);
});

usernameInput.addEventListener("change", saveNameToStorage);

async function fetchMessages() {
  try {
    const res = await fetch('/messages?after=' + lastId);
    if (!res.ok) { statusEl.textContent = "Offline"; statusEl.style.color = "#f87171"; return; }
    statusEl.textContent = "Online"; statusEl.style.color = "#7ee7b8";
    const data = await res.json();
    if (data.length > 0) {
      for (const m of data) {
        addMessageToDOM(m);
        lastId = Math.max(lastId, m.id);
      }
      chatEl.scrollTop = chatEl.scrollHeight;
    }
  } catch (e) {
    statusEl.textContent = "Offline";
    statusEl.style.color = "#f87171";
    console.error("fetch error", e);
  }
}

function friendlyTime(iso) {
  try {
    const d = new Date(iso + "Z"); // treat stored time as UTC
    return d.toLocaleString();
  } catch (e) { return iso; }
}

function addMessageToDOM(m) {
  const currentUser = (localStorage.getItem("local_chat_name") || "").trim() || null;
  const isMe = currentUser && m.username && m.username.trim() === currentUser;
  const row = document.createElement("div");
  row.className = "msg-row " + (isMe ? "me" : "you");

  const bubble = document.createElement("div");
  bubble.className = "bubble " + (isMe ? "me" : "you");

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = (m.username || "Anonymous") + " · " + friendlyTime(m.created_at);

  const text = document.createElement("div");
  text.innerHTML = m.text ? escapeHtml(m.text).replace(/\\n/g,'<br>') : "";

  bubble.appendChild(meta);
  bubble.appendChild(text);

  if (m.file_name) {
    const a = document.createElement("a");
    a.href = m.file_path;
    a.className = "file-link";
    a.textContent = "📎 " + m.file_name;
    a.target = "_blank";
    bubble.appendChild(a);
  }

  row.appendChild(bubble);
  chatEl.appendChild(row);
}

function escapeHtml(unsafe) {
  if (!unsafe) return "";
  return unsafe.replace(/[&<"'>]/g, function(m) {
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]);
  });
}

setInterval(fetchMessages, POLL_MS);
fetchMessages();

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = (usernameInput.value || localStorage.getItem("local_chat_name") || "Anonymous").trim();
  const formData = new FormData();
  formData.append("username", username);
  formData.append("text", msgbox.value);
  if (fileInput.files.length > 0) {
    formData.append("file", fileInput.files[0]);
  }
  const res = await fetch("/send", { method: "POST", body: formData });
  if (res.ok) {
    msgbox.value = "";
    fileInput.value = "";
    saveNameToStorage();
    await fetchMessages();
  } else {
    const txt = await res.text();
    alert("Error: " + txt);
  }
});

clearBtn.addEventListener("click", async () => {
  if (!confirm("Clear all messages? This deletes chat history and uploaded file references (files remain on disk).")) return;
  const res = await fetch("/clear", { method: "POST" });
  if (res.ok) {
    chatEl.innerHTML = "";
    lastId = 0;
    alert("Cleared chat (DB entries removed). Files remain in uploads/.");
  } else {
    alert("Clear failed");
  }
});
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/send", methods=["POST"])
def send():
    username = request.form.get("username", "Anonymous").strip()[:50]
    text = request.form.get("text", "").strip()
    file = request.files.get("file")
    file_name = None
    file_path = None

    if file and file.filename != "":
        filename = secure_filename(file.filename)
        if not allowed_file(filename):
            return f"File type not allowed. Allowed: {', '.join(ALLOWED_EXT)}", 400
        # ensure unique name: prefix timestamp
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        filename_stored = f"{ts}_{filename}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename_stored)
        file.save(save_path)
        file_name = filename
        file_path = url_for("uploaded_file", filename=filename_stored)

    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    cur = db.cursor()
    cur.execute("INSERT INTO messages (username, text, file_name, file_path, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, text, file_name, file_path, now))
    db.commit()
    return "ok", 200

@app.route("/messages")
def messages():
    after = int(request.args.get("after", 0))
    cur = db.cursor()
    if after > 0:
        cur.execute("SELECT id, username, text, file_name, file_path, created_at FROM messages WHERE id > ? ORDER BY id ASC", (after,))
    else:
        # return last 100 messages initially
        cur.execute("SELECT id, username, text, file_name, file_path, created_at FROM messages ORDER BY id DESC LIMIT 100")
    rows = cur.fetchall()
    rows_list = [dict(r) for r in reversed(rows)] if after == 0 else [dict(r) for r in rows]
    return jsonify(rows_list)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

@app.route("/clear", methods=["POST"])
def clear():
    cur = db.cursor()
    cur.execute("DELETE FROM messages")
    db.commit()
    return "cleared", 200

if __name__ == "__main__":
    # Listen on all interfaces so other LAN devices can access it
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
