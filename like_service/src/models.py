from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discussion_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
