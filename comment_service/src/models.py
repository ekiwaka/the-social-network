from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    discussion_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
