#!/usr/bin/env python3
"""
TempMail + SendMail Tool
Cool UI • Made by Shourya
"""

import os
import sys
import requests
import smtplib
from email.mime.text import MIMEText
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()
API_BASE = "https://www.1secmail.com/api/v1/"

# ========== TEMP MAIL FUNCTIONS ==========
def gen_mailbox():
    r = requests.get(API_BASE, params={"action": "genRandomMailbox", "count": 1})
    return r.json()[0]

def check_inbox(email):
    login, domain = email.split("@")
    r = requests.get(API_BASE, params={"action": "getMessages", "login": login, "domain": domain})
    return r.json()

def read_message(email, msg_id):
    login, domain = email.split("@")
    r = requests.get(API_BASE, params={
        "action": "readMessage", "login": login, "domain": domain, "id": msg_id
    })
    return r.json()

# ========== SEND EMAIL FUNCTION ==========
def send_email(sender, password, recipient, subject, body, smtp_server="smtp.gmail.com", smtp_port=587):
    msg = MIMEText(body, "plain")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, [recipient], msg.as_string())
    server.quit()

# ========== UI ==========
def banner():
    console.print(Panel.fit(
        "[bold cyan]📧 TempMail + Mailer[/bold cyan]\n[green]Cool UI - Made by Shourya[/green]",
        border_style="bright_magenta"
    ))

def main():
    banner()
    while True:
        console.print("\n[bold yellow]Options:[/bold yellow]")
        console.print("1. Generate Temp Mailbox")
        console.print("2. Check Inbox")
        console.print("3. Read Message")
        console.print("4. Send Email (SMTP)")
        console.print("5. Exit\n")

        choice = Prompt.ask("[bold cyan]Enter choice[/bold cyan]", choices=["1","2","3","4","5"])

        if choice == "1":
            email = gen_mailbox()
            console.print(Panel(f"[bold green]Your Temp Mailbox:[/bold green] {email}", border_style="green"))

        elif choice == "2":
            email = Prompt.ask("Enter your temp email")
            msgs = check_inbox(email)
            if not msgs:
                console.print("[red]Inbox empty[/red]")
            else:
                table = Table(title=f"Inbox for {email}")
                table.add_column("ID", style="cyan")
                table.add_column("From", style="yellow")
                table.add_column("Subject", style="green")
                table.add_column("Date", style="magenta")
                for m in msgs:
                    table.add_row(str(m["id"]), m["from"], m["subject"], m["date"])
                console.print(table)

        elif choice == "3":
            email = Prompt.ask("Enter your temp email")
            msg_id = Prompt.ask("Enter message ID")
            msg = read_message(email, msg_id)
            console.print(Panel(f"""
[bold cyan]From:[/bold cyan] {msg.get('from')}
[bold cyan]Subject:[/bold cyan] {msg.get('subject')}
[bold cyan]Date:[/bold cyan] {msg.get('date')}

[bold green]Body:[/bold green]
{msg.get('textBody') or "(No text body)"}
            """, border_style="cyan"))

        elif choice == "4":
            sender = Prompt.ask("Enter your sender email")
            password = Prompt.ask("Enter your email password (App Password for Gmail)", password=True)
            recipient = Prompt.ask("Enter recipient email")
            subject = Prompt.ask("Enter subject")
            body = Prompt.ask("Enter message body")

            try:
                send_email(sender, password, recipient, subject, body)
                console.print("[bold green]Email sent successfully![/bold green]")
            except Exception as e:
                console.print(f"[red]Failed to send: {e}[/red]")

        elif choice == "5":
            console.print("[bold magenta]Bye! Made by Shourya ❤[/bold magenta]")
            sys.exit()

if __name__ == "__main__":
    main()      </div>

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
