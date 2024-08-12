import os
from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from logging.handlers import RotatingFileHandler
import logging

app = Flask(__name__)

# Настройка пути к базе данных
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'books.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Настройка логирования
if not app.debug:
    if not os.path.exists('logs'):
        os.makedirs('logs')
    file_handler = RotatingFileHandler('logs/books_app.log', maxBytes=10240, backupCount=10)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info('Bookstore application startup')

# Модель книги
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    price = db.Column(db.String(20), nullable=False)
    image_url = db.Column(db.String(255))
    availability = db.Column(db.String(50), nullable=False)

# Функция поиска книг по запросу
def sclite(query, books):
    query = query.lower()
    matching_books = [book for book in books if query in book.title.lower()]
    return matching_books

# Главная страница для отображения всех книг и поиска
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        search_query = request.form.get('query', '')
        if search_query:
            books = sclite(search_query, Book.query.all())
        else:
            books = Book.query.all()
    else:
        books = Book.query.all()

    return render_template('index.html', books=books)

# Страница для добавления новой книги (форма)
@app.route('/add_book', methods=['GET', 'POST'])
def add_book_form():
    if request.method == 'POST':
        try:
            data = request.form
            new_book = Book(
                title=data['title'],
                price=data['price'],
                image_url=data['image_url'],
                availability=data['availability']
            )
            db.session.add(new_book)
            db.session.commit()
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error adding book: {e}")
            return render_template('edit_book.html', title='Add New Book', action='/add_book', error=str(e), book=None)

    return render_template('edit_book.html', title='Add New Book', action='/add_book', book=None)

# Страница для редактирования книги (форма)
@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book_form(book_id):
    book = Book.query.get(book_id)
    if request.method == 'POST':
        try:
            data = request.form
            book.title = data['title']
            book.price = data['price']
            book.image_url = data['image_url']
            book.availability = data['availability']
            db.session.commit()
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error editing book: {e}")
            return render_template('edit_book.html', title='Edit Book', action=f'/edit_book/{book_id}', error=str(e), book=book)

    return render_template('edit_book.html', title='Edit Book', action=f'/edit_book/{book_id}', book=book)

# Обработка запроса для удаления книги
@app.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    try:
        book = Book.query.get(book_id)
        db.session.delete(book)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error deleting book: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True)
