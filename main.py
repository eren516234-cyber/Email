#!/data/data/com.termux/files/usr/bin/python3
# termux_mail.py - npyscreen TUI to send email via SMTP
import npyscreen
import smtplib
from email.message import EmailMessage

class MailForm(npyscreen.ActionForm):
    def create(self):
        self.smtp_host = self.add(npyscreen.TitleText, name="SMTP Host:", value="smtp.mailtrap.io")
        self.smtp_port = self.add(npyscreen.TitleText, name="Port:", value="587")
        self.username = self.add(npyscreen.TitleText, name="Username:")
        self.password = self.add(npyscreen.TitlePassword, name="Password:")
        self.from_addr = self.add(npyscreen.TitleText, name="From:", value="no-reply@yourdomain.com")
        self.to = self.add(npyscreen.TitleText, name="To:", value="recipient@yourdomain.com")
        self.subject = self.add(npyscreen.TitleText, name="Subject:", value="Test email from Termux")
        self.body = self.add(npyscreen.MultiLineEdit, value="Hello,\n\nThis is a test from Termux.\n", max_height=10, rely=12)

    def on_ok(self):
        # Build email
        msg = EmailMessage()
        msg['From'] = self.from_addr.value
        msg['To'] = self.to.value
        msg['Subject'] = self.subject.value
        msg.set_content(self.body.value)

        try:
            port = int(self.smtp_port.value or 587)
            with smtplib.SMTP(self.smtp_host.value, port, timeout=15) as server:
                server.ehlo()
                if port == 587:
                    server.starttls()
                    server.ehlo()
                if self.username.value:
                    server.login(self.username.value, self.password.value)
                server.send_message(msg)
            npyscreen.notify_confirm("Message sent successfully!", title="Success")
        except Exception as e:
            npyscreen.notify_confirm(f"Failed to send: {e}", title="Error")

    def on_cancel(self):
        self.parentApp.setNextForm(None)

class MailApp(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm("MAIN", MailForm, name="Termux Mail Tool")

if __name__ == "__main__":
    app = MailApp()
    app.run()