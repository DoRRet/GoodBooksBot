import pandas as pd
import sqlite3

def update_books_from_excel(excel_file):
    # Чтение данных из Excel
    df = pd.read_excel(excel_file)

    # Вывод заголовков столбцов для проверки
    print(df.columns)

    # Выбор нужных столбцов
    df = df[['Наименование', 'Цена продажи']]

    # Переименование столбцов
    df.columns = ['title', 'price']

    # Добавление столбцов для наличия и URL изображения
    df['availability'] = 'В наличии'
    df['image_url'] = ""

    # Подключение к базе данных
    conn = sqlite3.connect('books.db')
    cursor = conn.cursor()

    # Очистка таблицы Books
    cursor.execute("DELETE FROM Book")

    # Перебор строк DataFrame и добавление их в базу данных
    for index, row in df.iterrows():
        title = row['title']
        price = row['price']
        availability = row['availability']
        image_url = row['image_url']

        # Вставка новой записи в таблицу Book
        cursor.execute(
            "INSERT INTO Book (title, price, availability, image_url) VALUES (?, ?, ?, ?)",
            (title, price, availability, image_url)
        )

    # Подтверждение изменений и закрытие соединения с базой данных
    conn.commit()
    conn.close()

    print("Данные успешно перенесены из Excel в SQLite!")
