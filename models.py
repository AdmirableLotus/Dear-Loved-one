from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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

