import tkinter as tk
from tkinter import scrolledtext, ttk
import transformers
import requests
from bs4 import BeautifulSoup
import traceback
import difflib

# Branding
BRANDING = """
  _____   _____  _____   _   _
 |  ___| |  _  ||  _  | | | | |
 | |__   | | | || | | | | | | |
 |  __|  | | | || | | | | | | |
 | |___  |  _  ||  _  | | |_| |
 |_____| |_| |_||_| |_| |_____|
          By Shourya
"""

# LLM Models
MODEL_NAMES = {
    "GPT-2": "gpt2",
    "GPT-Neo": "EleutherAI/gpt-neo-1.3B",
}

# Known words list for autocorrect
known_words = [
    "python", "function", "variable", "loop", "class", "import",
    "tkinter", "code", "generate", "search", "tool"
]

# Function to generate code using LLM
def generate_code(prompt, model_name="gpt2", max_length=150):
    try:
        tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)
        model = transformers.AutoModelForCausalLM.from_pretrained(model_name)
        input_ids = tokenizer.encode(prompt, return_tensors="pt")
        output = model.generate(input_ids, max_length=max_length, num_return_sequences=1, no_repeat_ngram_size=2)
        generated_code = tokenizer.decode(output[0], skip_special_tokens=True)
        return generated_code
    except Exception as e:
        print(f"Error generating code: {e}")
        traceback.print_exc()
        return None

# Function to search the web for code snippets
def search_web(query):
    try:
        search_url = f"https://www.google.com/search?q={query}"
        response = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        code_snippets = [code_tag.text for code_tag in soup.find_all("code")]
        return code_snippets
    except requests.exceptions.RequestException as e:
        print(f"Error during web search: {e}")
        return []
    except Exception as e:
        print(f"Error parsing web results: {e}")
        traceback.print_exc()
        return []

# Function to create a new tool (Python file)
def create_tool(tool_name, code):
    try:
        file_name = f"{tool_name}.py"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"Tool '{tool_name}' created as '{file_name}'")
    except Exception as e:
        print(f"Error creating tool: {e}")
        traceback.print_exc()

# Autocorrection function
def autocorrect(text):
    words = text.split()
    corrected_words = []
    for word in words:
        if word in known_words:
            corrected_words.append(word)
        else:
            closest_match = difflib.get_close_matches(word, known_words, n=1, cutoff=0.6)
            corrected_words.append(closest_match[0] if closest_match else word)
    return " ".join(corrected_words)

# Example usage
if __name__ == "__main__":
    sample_text = "pythn functon varable"
    print("Original:", sample_text)
    print("Autocorrected:", autocorrect(sample_text))      <div style="flex:1">
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
