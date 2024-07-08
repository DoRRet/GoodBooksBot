from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель книги
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    price = db.Column(db.String(20), nullable=False)
    image_url = db.Column(db.String(255))
    availability = db.Column(db.String(50), nullable=False)

# Главная страница для отображения всех книг и поиска
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        columns = request.form.getlist('columns')

        if not query:
            books = Book.query.all()
        else:
            # Создаем динамический фильтр для каждого выбранного столбца
            filters = []
            for column in columns:
                if column == 'title':
                    filters.append(Book.title.ilike(f'%{query}%'))
                elif column == 'price':
                    filters.append(Book.price.ilike(f'%{query}%'))
                elif column == 'availability':
                    filters.append(Book.availability.ilike(f'%{query}%'))
                elif column == 'image_url':
                    filters.append(Book.image_url.ilike(f'%{query}%'))

            # Объединяем все фильтры в один запрос с использованием оператора OR
            books = Book.query.filter(or_(*filters)).all()
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
            return render_template('edit_book.html', title='Edit Book', action=f'/edit_book/{book_id}', error=str(e), book=book)

    return render_template('edit_book.html', title='Edit Book', action=f'/edit_book/{book_id}', book=book)

# Обработка запроса для удаления книги
@app.route('/delete_book/<int:book_id>', methods=['GET'])
def delete_book(book_id):
    try:
        book = Book.query.get(book_id)
        db.session.delete(book)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=5000)