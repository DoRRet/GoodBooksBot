from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/LeoLorenco/GoodBooksBot/books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    price = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(300), nullable=True)
    availability = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<Book {self.title}>'