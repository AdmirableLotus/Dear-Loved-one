from datetime import datetime, timezone
import os, smtplib
from email.message import EmailMessage

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from email_validator import validate_email, EmailNotValidError

from models import db, User, Memory, Message

# --------------------------------------------------------------------
# Config
# --------------------------------------------------------------------
load_dotenv()

# Using Flask-SQLAlchemy only; standalone SQLAlchemy engine removed.

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
"""
Flask-SQLAlchemy configuration for Message model (models.py).
Uses the same SQLite file as the existing SQLAlchemy engine.
"""
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///dlo.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    # Ensure all Flask-SQLAlchemy models have tables
    db.create_all()

login_manager = LoginManager(app)
login_manager.login_view = "login"

# Models are defined in models.py using Flask-SQLAlchemy

# --------------------------------------------------------------------
# Login manager
# --------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))

# --------------------------------------------------------------------
# Email (prints to console if SMTP not configured)
# --------------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or 587)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@dlo.local")

def send_email(recipient: str, subject: str, body: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = recipient
    msg.set_content(body)

    if not SMTP_HOST:
        print("\n=== EMAIL (simulated) ===")
        print(msg)
        print("=========================\n")
        return True

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            if SMTP_USER and SMTP_PASS:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        print("Email send failed:", e)
        return False

# --------------------------------------------------------------------
# Background job: deliver due messages
# --------------------------------------------------------------------
def deliver_due_flask():
    now = datetime.now(timezone.utc)
    with app.app_context():
        due = (
            Memory.query
            .filter(Memory.status == "scheduled", Memory.send_at <= now)
            .all()
        )
        for m in due:
            ok = send_email(
                m.recipient_email,
                f"[Dear Loved One] {m.title}",
                f"You have received a message:\n\n{m.message}\n\nSent via Dear Loved One",
            )
            if ok:
                m.status = "sent"
                m.sent_at = datetime.now(timezone.utc)
            else:
                m.status = "failed"
        if due:
            db.session.commit()
def deliver_due():
    return deliver_due_flask()
    with DBSession(engine) as db:
        due = db.query(Memory).filter(Memory.status == "scheduled", Memory.send_at <= now).all()
        for m in due:
            ok = send_email(
                m.recipient_email,
                f"[Dear Loved One] {m.title}",
                f"You have received a message:\n\n{m.message}\n\n— Sent via Dear Loved One",
            )
            if ok:
                m.status = "sent"
                m.sent_at = datetime.now(timezone.utc)
            else:
                m.status = "failed"
        if due:
            db.commit()

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(deliver_due_flask, "interval", seconds=60, id="deliver_due")
scheduler.start()

# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------
@app.get("/")
def index():
    return render_template("index.html")

@app.get("/register")
def register():
    return render_template("register.html")

@app.post("/register")
def register_post():
    name = request.form.get("name","").strip()
    email = request.form.get("email","").strip().lower()
    password = request.form.get("password","")
    try:
        validate_email(email)
    except EmailNotValidError as e:
        flash(str(e), "error"); return redirect(url_for("register"))
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error"); return redirect(url_for("register"))

    if db.session.query(User).filter_by(email=email).first():
        flash("Email already registered.", "error"); return redirect(url_for("register"))
    u = User(email=email, name=name)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    flash("Account created. Please log in.", "ok")
    return redirect(url_for("login"))

@app.get("/login")
def login():
    return render_template("login.html")

@app.post("/login")
def login_post():
    email = request.form.get("email","").strip().lower()
    password = request.form.get("password","")
    u = db.session.query(User).filter_by(email=email).first()
    if not u or not u.check_password(password):
        flash("Invalid credentials.", "error"); return redirect(url_for("login"))
    login_user(u)
    return redirect(url_for("dashboard"))

@app.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.get("/dashboard")
@login_required
def dashboard():
    mems = (
        db.session.query(Memory)
        .filter_by(user_id=current_user.id)
        .order_by(Memory.created_at.desc())
        .all()
    )
    return render_template("dashboard.html", memories=mems)

@app.post("/memories")
@login_required
def create_memory():
    title = request.form.get("title","").strip()
    recipient = request.form.get("recipient","").strip()
    message = request.form.get("message","").strip()
    # incoming send_at is local datetime string; convert to UTC
    send_at_local = request.form.get("send_at","").strip()
    try:
        validate_email(recipient)
    except EmailNotValidError as e:
        flash(f"Recipient email: {e}", "error"); return redirect(url_for("dashboard"))
    if not title or not message or not send_at_local:
        flash("All fields are required.", "error"); return redirect(url_for("dashboard"))

    # parse local and treat as naive local -> assume local is current server tz; convert to UTC
    dt = datetime.fromisoformat(send_at_local)  # naive local
    dt_utc = dt.replace(tzinfo=timezone.utc)    # (simple demo assumption)

    m = Memory(
        user_id=current_user.id,
        title=title,
        recipient_email=recipient,
        message=message,
        send_at=dt_utc,
    )
    db.session.add(m)
    db.session.commit()
    flash("Memory scheduled.", "ok")
    return redirect(url_for("dashboard"))

@app.post("/memories/<int:mid>/send_now")
@login_required
def send_now(mid):
    m = db.session.get(Memory, mid)
    if not m or m.user_id != current_user.id:
        return ("Not found", 404)
    ok = send_email(m.recipient_email, f"[Dear Loved One] {m.title}", m.message)
    if ok:
        m.status = "sent"; m.sent_at = datetime.now(timezone.utc)
        db.session.commit(); flash("Sent now.", "ok")
    else:
        m.status = "failed"; db.session.commit(); flash("Send failed.", "error")
    return redirect(url_for("dashboard"))

@app.post("/memories/<int:mid>/delete")
@login_required
def delete_memory(mid):
    m = db.session.get(Memory, mid)
    if not m or m.user_id != current_user.id:
        return ("Not found", 404)
    db.session.delete(m); db.session.commit()
    flash("Deleted.", "ok")
    return redirect(url_for("dashboard"))

# --------------------------------------------------------------------
# Message routes (Flask-SQLAlchemy)
# --------------------------------------------------------------------
@app.route("/messages")
@login_required
def messages():
    all_messages = Message.query.filter_by(user_id=current_user.id).order_by(Message.delivery_date.desc()).all()
    return render_template("messages.html", messages=all_messages)


@app.route("/messages/new", methods=["GET", "POST"])
@login_required
def new_message():
    if request.method == "POST":
        recipient = request.form["recipient"]
        content = request.form["content"]
        delivery_date = datetime.strptime(request.form["delivery_date"], "%Y-%m-%d")
        new_msg = Message(
            recipient=recipient,
            content=content,
            delivery_date=delivery_date,
            user_id=current_user.id,
        )
        db.session.add(new_msg)
        db.session.commit()
        flash("Message created successfully!", "success")
        return redirect(url_for("messages"))
    return render_template("new_message.html")


@app.route("/messages/<int:id>")
@login_required
def view_message(id):
    message = Message.query.get_or_404(id)
    if message.user_id != current_user.id:
        return ("Not found", 404)
    return render_template("view_message.html", message=message)


@app.route("/messages/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_message(id):
    message = Message.query.get_or_404(id)
    if message.user_id != current_user.id:
        return ("Not found", 404)
    if request.method == "POST":
        message.recipient = request.form["recipient"]
        message.content = request.form["content"]
        message.delivery_date = datetime.strptime(request.form["delivery_date"], "%Y-%m-%d")
        db.session.commit()
        flash("Message updated successfully!", "info")
        return redirect(url_for("messages"))
    return render_template("edit_message.html", message=message)


@app.route("/messages/<int:id>/delete")
@login_required
def delete_message(id):
    message = Message.query.get_or_404(id)
    if message.user_id != current_user.id:
        return ("Not found", 404)
    db.session.delete(message)
    db.session.commit()
    flash("Message deleted successfully!", "danger")
    return redirect(url_for("messages"))

if __name__ == "__main__":
    app.run(debug=True)
