import pandas as pd
import sqlite3
# pip install xlrd
# Загрузка данных из Excel
excel_file = 'tovar.xls'  # Укажите путь к вашему файлу Excel
df = pd.read_excel(excel_file)

# Оставляем только нужные столбцы: наименование и цена продажи
df = df[['Наименование', 'Цена продажи']]

# Переименуем столбцы для соответствия базе данных
df.columns = ['title', 'price']


df['availability'] = 'В наличии'

# Добавляем столбец 'image_url' с пустыми значениями
df['image_url'] = ""

# Подключение к базе данных SQLite
conn = sqlite3.connect('books.db')
cursor = conn.cursor()

# Для каждой строки в DataFrame обновляем или вставляем запись в базу данных
for index, row in df.iterrows():
    title = row['title']
    price = row['price']
    availability = row['availability']
    image_url = row['image_url']

    # Проверка на наличие записи с таким же названием
    cursor.execute("SELECT * FROM Book WHERE title = ?", (title,))
    result = cursor.fetchone()

    if result:
        # Если запись существует, обновляем только цену и доступность
        cursor.execute(
            "UPDATE Book SET price = ?, availability = ? WHERE title = ?",
            (price, availability, title)
        )
    else:
        # Если записи нет, вставляем новую строку
        cursor.execute(
            "INSERT INTO Book (title, price, availability, image_url) VALUES (?, ?, ?, ?)",
            (title, price, availability, image_url)
        )

# Сохранение изменений и закрытие подключения
conn.commit()
conn.close()

print("Данные успешно перенесены из Excel в SQLite!")