from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# Minimal shadow of the existing users table so FK resolves
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    memories = db.relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    messages = db.relationship("Message", backref="owner", cascade="all, delete-orphan")

    def set_password(self, pw: str):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw: str) -> bool:
        return check_password_hash(self.password_hash, pw)


class Memory(db.Model):
    __tablename__ = "memories"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    recipient_email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    send_at = db.Column(db.DateTime(timezone=True), nullable=False)  # UTC
    status = db.Column(db.String(20), default="scheduled")  # scheduled|sent|failed
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", back_populates="memories")


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    delivery_date = db.Column(db.DateTime, nullable=False)
    sent = db.Column(db.Boolean, default=False)
    # Match existing users table name in app.py ("users")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __repr__(self):
        return f"<Message {self.id} to {self.recipient}>"
