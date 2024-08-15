from flask import Flask, request, render_template, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from logging.handlers import RotatingFileHandler
import logging
import os
from werkzeug.utils import secure_filename
from check_db import update_books_from_excel

app = Flask(__name__)

app.secret_key = b'\xf0\x1d\x19\xa3\xcb\x11\xbc\xe5\xa4\xf4\xcc\x08\xd2\x18\x1f\xcf\x90\x8e\x8c\xa7\x9c\x7f\x88'

# Настройка пути к базе данных
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'books.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Папка для загрузки файлов
app.config['ALLOWED_EXTENSIONS'] = {'xls', 'xlsx'}
db = SQLAlchemy(app)

# Создание папки для загрузки файлов, если она не существует
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


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
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255))
    availability = db.Column(db.String(50), nullable=False)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Новый маршрут для загрузки Excel-файла
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            update_books_from_excel(file_path)  # Обновление данных в базе
            flash('Файл успешно загружен и обработан.')
            
            return redirect(url_for('index'))
    
    return render_template('upload.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Количество книг на одной странице

        if request.method == 'POST':
            search_query = request.form.get('query', '').lower()  # Приведение запроса к нижнему регистру
        else:
            search_query = request.args.get('query', '').lower()  # Приведение запроса к нижнему регистру

        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        availability = request.args.get('availability', '')

        books_query = Book.query

        if search_query:
            books_query = books_query.filter(Book.title.ilike(f'%{search_query}%'))
        if min_price is not None:
            books_query = books_query.filter(Book.price >= min_price)
        if max_price is not None:
            books_query = books_query.filter(Book.price <= max_price)
        if availability:
            books_query = books_query.filter(Book.availability == availability)

        pagination = books_query.paginate(page=page, per_page=per_page, error_out=False)
        books = pagination.items

        # Добавлено для отображения общего количества книг
        total_books = books_query.count()

        return render_template('index.html', books=books, pagination=pagination, query=search_query, min_price=min_price, max_price=max_price, availability=availability, total_books=total_books)
    except Exception as e:
        app.logger.error(f"Error in index route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/add_book', methods=['GET', 'POST'])
def add_book_form():
    if request.method == 'POST':
        try:
            data = request.form

            new_book = Book(
                title=data['title'],
                price=float(data['price']),
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

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book_form(book_id):
    book = Book.query.get(book_id)
    if request.method == 'POST':
        try:
            data = request.form
            book.title = data['title']
            book.price = float(data['price'])
            book.image_url = data['image_url']
            book.availability = data['availability']
            db.session.commit()
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error editing book: {e}")
            return render_template('edit_book.html', title='Edit Book', action=f'/edit_book/{book_id}', error=str(e), book=book)

    return render_template('edit_book.html', title='Edit Book', action=f'/edit_book/{book_id}', book=book)

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
