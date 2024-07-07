from flask import Flask, request, jsonify, render_template, redirect, url_for
from config import app, db, Book

# Главная страница для отображения всех книг
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form.get('query', '')
        column = request.form.get('column', 'all')
        if column == 'title':
            books = Book.query.filter(Book.title.ilike(f'%{query}%')).all()
        elif column == 'author':
            books = Book.query.filter(Book.author.ilike(f'%{query}%')).all()
        elif column == 'genre':
            books = Book.query.filter(Book.genre.ilike(f'%{query}%')).all()
        else:
            books = Book.query.filter(
                (Book.title.ilike(f'%{query}%')) |
                (Book.author.ilike(f'%{query}%')) |
                (Book.genre.ilike(f'%{query}%'))
            ).all()
    else:
        books = Book.query.all()
    return render_template('index.html', books=books)

# Страница для добавления новой книги (форма)
@app.route('/add_book', methods=['GET'])
def add_book_form():
    return render_template('edit_book.html', title='Add New Book', action='/add_book', book=None)

# Обработка POST запроса для добавления новой книги
@app.route('/add_book', methods=['POST'])
def add_book():
    try:
        data = request.form
        new_book = Book(title=data['title'], author=data['author'], genre=data['genre'])
        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Страница для редактирования книги (форма)
@app.route('/edit_book/<int:book_id>', methods=['GET'])
def edit_book_form(book_id):
    book = Book.query.get(book_id)
    return render_template('edit_book.html', title='Edit Book', action=f'/edit_book/{book_id}', book=book)

# Обработка POST запроса для редактирования книги
@app.route('/edit_book/<int:book_id>', methods=['POST'])
def edit_book(book_id):
    try:
        data = request.form
        book = Book.query.get(book_id)
        book.title = data['title']
        book.author = data['author']
        book.genre = data['genre']
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    app.run(host='0.0.0.0', port=5000)