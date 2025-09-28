#!/usr/bin/env python3
"""
TempMail + SendMail Tool
Cool Terminal UI • Made by Shourya
"""

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

# ========== TEMP MAIL ==========
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

# ========== SEND EMAIL ==========
def send_email(sender, password, recipient, subject, body,
               smtp_server="smtp.gmail.com", smtp_port=587):
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
        "[bold cyan]📧 TempMail + Mailer[/bold cyan]\n[green]Cool Terminal UI - Made by Shourya[/green]",
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
                console.print("[bold green]✅ Email sent successfully![/bold green]")
            except Exception as e:
                console.print(f"[red]❌ Failed to send: {e}[/red]")

        elif choice == "5":
            console.print("[bold magenta]👋 Bye! Made by Shourya ❤[/bold magenta]")
            sys.exit()

if __name__ == "__main__":
    main()
