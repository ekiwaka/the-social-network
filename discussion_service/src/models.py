from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255), nullable=True)
    hashtags = db.Column(db.String(255), nullable=True)
