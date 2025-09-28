#!/usr/bin/env python3
"""
anonmail.py
Termux-friendly anonymous email helper:
 - create mail.tm accounts over Tor (optional)
 - list/read mail.tm messages
 - send emails via SMTP routed through Tor (optional)
 - strip EXIF from image attachments (Pillow)
 - optional encrypted credential storage (AES-GCM via pycryptodome)
Dependencies: requests, pysocks, Pillow, pycryptodome
Usage: python anonmail.py --help
"""

import argparse, os, sys, json, time, getpass, mimetypes, io, base64
import requests, socks, socket, smtplib
from email.message import EmailMessage
from PIL import Image, UnidentifiedImageError

# Optional crypto (pycryptodome)
try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    import hashlib
    HAS_CRYPTO = True
except Exception:
    HAS_CRYPTO = False

# Default mail.tm API
API_BASE = "https://api.mail.tm"

# Where to store encrypted creds
DATA_DIR = os.path.expanduser("~/.termux_anon_mail")
os.makedirs(DATA_DIR, exist_ok=True)
CREDS_FILE = os.path.join(DATA_DIR, "creds.json.enc")  # encrypted blob if used

# ---------------------- Utilities ----------------------
def make_tor_session():
    s = requests.Session()
    s.proxies = {
        "http":  "socks5h://127.0.0.1:9050",
        "https": "socks5h://127.0.0.1:9050",
    }
    return s

def enable_tor_socket():
    # route all socket connections through Tor (socks5)
    socks.setdefaultproxy(socks.SOCKS5, "127.0.0.1", 9050)
    socks.wrapmodule(socket)

def guess_mime(path):
    ctype, _ = mimetypes.guess_type(path)
    if ctype:
        maintype, subtype = ctype.split("/", 1)
    else:
        maintype, subtype = "application", "octet-stream"
    return maintype, subtype

# ---------------------- EXIF stripping ----------------------
def strip_exif_bytes(path):
    """Open image, strip EXIF, return bytes (PNG/JPEG saved)"""
    try:
        img = Image.open(path)
    except UnidentifiedImageError:
        raise RuntimeError("File is not an image or unsupported image format.")
    out = io.BytesIO()
    # save in same format but without exif
    fmt = img.format if img.format else "PNG"
    # convert to RGB to avoid issues with some PNG modes
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    img.save(out, format=fmt)
    return out.getvalue()

# ---------------------- mail.tm integration ----------------------
def get_domains(session=None):
    session = session or requests
    r = session.get(f"{API_BASE}/domains")
    r.raise_for_status()
    data = r.json()
    # handle different response shapes
    members = data.get("hydra:member") or data.get("data") or []
    if isinstance(members, list) and members:
        return [d.get("domain") for d in members if d.get("domain")]
    # fallback parse
    return []

def random_localpart(n=10):
    import random, string
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def create_mailtm_account(address=None, password=None, use_tor=False):
    session = make_tor_session() if use_tor else requests
    domains = get_domains(session=session)
    if not domains:
        raise RuntimeError("No mail.tm domains available.")
    domain = domains[0]
    if address and "@" not in address:
        address = f"{address}@{domain}"
    if not address:
        address = f"{random_localpart()}@{domain}"
    if not password:
        import random, string
        password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(14))
    payload = {"address": address, "password": password}
    r = session.post(f"{API_BASE}/accounts", json=payload)
    # 201 = created, 400 may mean already exists
    if r.status_code not in (201, 400):
        r.raise_for_status()
    # get token
    tokr = session.post(f"{API_BASE}/token", json={"address": address, "password": password})
    if tokr.status_code != 200:
        raise RuntimeError(f"Failed to obtain token: {tokr.status_code} {tokr.text}")
    token = tokr.json().get("token")
    return address, password, token

def list_messages(token, use_tor=False, limit=10):
    session = make_tor_session() if use_tor else requests
    headers = {"Authorization": f"Bearer {token}"}
    r = session.get(f"{API_BASE}/messages", headers=headers, params={"page":1,"perPage":limit})
    r.raise_for_status()
    data = r.json()
    members = data.get("hydra:member") or data.get("data") or []
    return members

def get_message(token, message_id, use_tor=False):
    session = make_tor_session() if use_tor else requests
    headers = {"Authorization": f"Bearer {token}"}
    r = session.get(f"{API_BASE}/messages/{message_id}", headers=headers)
    r.raise_for_status()
    return r.json()

# ---------------------- Credential encryption (AES-GCM with PBKDF2) ----------------------
PBKDF2_ITERS = 200_000
SALT_LEN = 16
NONCE_LEN = 12
KEY_LEN = 32  # AES-256

def derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, PBKDF2_ITERS, dklen=KEY_LEN)

def encrypt_blob(plaintext_bytes: bytes, passphrase: str) -> bytes:
    if not HAS_CRYPTO:
        raise RuntimeError("pycryptodome not installed; cannot encrypt.")
    salt = get_random_bytes(SALT_LEN)
    key = derive_key(passphrase, salt)
    nonce = get_random_bytes(NONCE_LEN)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(plaintext_bytes)
    blob = salt + nonce + tag + ct
    return base64.b64encode(blob)

def decrypt_blob(b64blob: bytes, passphrase: str) -> bytes:
    if not HAS_CRYPTO:
        raise RuntimeError("pycryptodome not installed; cannot decrypt.")
    blob = base64.b64decode(b64blob)
    salt = blob[:SALT_LEN]
    nonce = blob[SALT_LEN:SALT_LEN+NONCE_LEN]
    tag = blob[SALT_LEN+NONCE_LEN:SALT_LEN+NONCE_LEN+16]
    ct = blob[SALT_LEN+NONCE_LEN+16:]
    key = derive_key(passphrase, salt)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ct, tag)
    return plaintext

def save_creds(data: dict, passphrase: str = None):
    b = json.dumps(data).encode("utf-8")
    if passphrase:
        enc = encrypt_blob(b, passphrase)
        with open(CREDS_FILE, "wb") as f:
            f.write(enc)
        print("[saved encrypted]", CREDS_FILE)
    else:
        # plaintext save (warning)
        with open(CREDS_FILE + ".plain.json", "wb") as f:
            f.write(b)
        print("[saved plaintext] to", CREDS_FILE + ".plain.json")

def load_creds(passphrase: str = None):
    if passphrase:
        if not os.path.exists(CREDS_FILE):
            raise RuntimeError("Encrypted creds file not found.")
        with open(CREDS_FILE, "rb") as f:
            enc = f.read()
        data = decrypt_blob(enc, passphrase)
        return json.loads(data.decode("utf-8"))
    else:
        p = CREDS_FILE + ".plain.json"
        if not os.path.exists(p):
            raise RuntimeError("Plaintext creds not found. Use --passphrase to decrypt encrypted file.")
        with open(p, "rb") as f:
            data = f.read()
        return json.loads(data.decode("utf-8"))

# ---------------------- SMTP send (with Tor option) ----------------------
def send_email_smtp(smtp_server, smtp_port, username, password,
                    from_addr, to_addrs, subject, body, attachments=None,
                    use_tls=True, use_tor=False, strip_exif=True):
    if isinstance(to_addrs, str):
        to_addrs = [a.strip() for a in to_addrs.split(",") if a.strip()]

    if use_tor:
        enable_tor_socket()

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.set_content(body)

    if attachments:
        for path in attachments:
            path = os.path.expanduser(path)
            if not os.path.exists(path):
                print("[warn] attachment missing:", path)
                continue
            try:
                if strip_exif and any(path.lower().endswith(ext) for ext in (".jpg",".jpeg",".png",".webp",".bmp",".tiff",".gif")):
                    data = strip_exif_bytes(path)
                    maintype, subtype = guess_mime(path)
                    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(path))
                else:
                    with open(path, "rb") as f:
                        data = f.read()
                    maintype, subtype = guess_mime(path)
                    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(path))
            except Exception as e:
                print("[warn] failed attach:", e)
                continue

    try:
        if str(smtp_port) == "465":
            server = smtplib.SMTP_SSL(smtp_server, int(smtp_port), timeout=30)
        else:
            server = smtplib.SMTP(smtp_server, int(smtp_port), timeout=30)
            if use_tls:
                server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        print("Email sent.")
    except Exception as e:
        raise RuntimeError("SMTP send failed: " + str(e))

# ---------------------- CLI ----------------------
def main():
    p = argparse.ArgumentParser(description="AnonMail - Termux anonymous email helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    c1 = sub.add_parser("create-temp", help="Create disposable mail.tm account")
    c1.add_argument("--address", help="localpart or full address (optional)")
    c1.add_argument("--password", help="password (optional)")
    c1.add_argument("--use-tor", action="store_true", help="route account creation via Tor")

    c2 = sub.add_parser("list", help="List messages for token")
    c2.add_argument("--token", required=True)
    c2.add_argument("--use-tor", action="store_true")

    c3 = sub.add_parser("read", help="Read message by id")
    c3.add_argument("--token", required=True)
    c3.add_argument("--id", required=True)
    c3.add_argument("--use-tor", action="store_true")

    c4 = sub.add_parser("send", help="Send email via SMTP")
    c4.add_argument("--smtp-server", required=True)
    c4.add_argument("--smtp-port", required=True, type=int)
    c4.add_argument("--smtp-user", required=True)
    c4.add_argument("--smtp-pass", required=True)
    c4.add_argument("--from", dest="from_addr", required=True)
    c4.add_argument("--to", required=True)
    c4.add_argument("--subject", default="(no subject)")
    c4.add_argument("--body", default="")
    c4.add_argument("--attachment", action="append")
    c4.add_argument("--no-tls", action="store_true")
    c4.add_argument("--use-tor", action="store_true")
    c4.add_argument("--no-strip-exif", action="store_true", help="do NOT strip exif from attachments")

    c5 = sub.add_parser("save-creds", help="Save SMTP creds encrypted with passphrase")
    c5.add_argument("--smtp-user", required=True)
    c5.add_argument("--smtp-pass", required=True)
    c5.add_argument("--smtp-server", required=True)
    c5.add_argument("--smtp-port", required=True, type=int)

    c6 = sub.add_parser("show-creds", help="Show saved creds (decrypt with passphrase)")
    c6.add_argument("--passphrase", help="passphrase to decrypt saved creds")

    args = p.parse_args()
    try:
        if args.cmd == "create-temp":
            addr, pw, token = create_mailtm_account(address=args.address, password=args.password, use_tor=args.use_tor)
            print("[created]", addr)
            print("password:", pw)
            print("token:", token)
            print("USE token to list/read: python anonmail.py list --token <token>")
        elif args.cmd == "list":
            msgs = list_messages(args.token, use_tor=args.use_tor)
            if not msgs:
                print("No messages.")
            for m in msgs:
                print("ID:", m.get("id"))
                print("From:", m.get("from"))
                print("Subject:", m.get("subject"))
                print("Preview:", m.get("intro"))
                print("---")
        elif args.cmd == "read":
            m = get_message(args.token, args.id, use_tor=args.use_tor)
            print("From:", m.get("from"))
            print("Subject:", m.get("subject"))
            print("Date:", m.get("createdAt"))
            print("Text:\n", m.get("text") or m.get("html") or "(no text)")
            if m.get("attachments"):
                print("Attachments metadata present:", m.get("attachments"))
        elif args.cmd == "send":
            send_email_smtp(
                smtp_server=args.smtp_server,
                smtp_port=args.smtp_port,
                username=args.smtp_user,
                password=args.smtp_pass,
                from_addr=args.from_addr,
                to_addrs=args.to,
                subject=args.subject,
                body=args.body,
                attachments=args.attachment,
                use_tls=not args.no_tls,
                use_tor=args.use_tor,
                strip_exif=not args.no_strip_exif
            )
        elif args.cmd == "save-creds":
            if not HAS_CRYPTO:
                print("Warning: pycryptodome not installed; saved will be plaintext file.")
                save_creds({
                    "smtp_server": args.smtp_server,
                    "smtp_port": args.smtp_port,
                    "smtp_user": args.smtp_user,
                    "smtp_pass": args.smtp_pass
                }, passphrase=None)
            else:
                passphrase = getpass.getpass("Enter passphrase to encrypt creds: ")
                confirm = getpass.getpass("Confirm passphrase: ")
                if passphrase != confirm:
                    print("Passphrases do not match.")
                    sys.exit(1)
                save_creds({
                    "smtp_server": args.smtp_server,
                    "smtp_port": args.smtp_port,
                    "smtp_user": args.smtp_user,
                    "smtp_pass": args.smtp_pass
                }, passphrase=passphrase)
        elif args.cmd == "show-creds":
            if args.passphrase:
                d = load_creds(passphrase=args.passphrase)
                print(json.dumps(d, indent=2))
            else:
                try:
                    d = load_creds(passphrase=None)
                    print(json.dumps(d, indent=2))
                except Exception as e:
                    print("Failed to load creds:", e)
                    print("If you saved encrypted creds, call --passphrase <pass>")
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
