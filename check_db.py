import os
import sqlite3

print(f"Текущий рабочий каталог: {os.getcwd()}")

# Печать полного пути к скрипту
print(f"Полный путь к файлу: {os.path.abspath(__file__)}")

# Определение пути к базе данных, как в app.py
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'books.db')

def check_books():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM Book")
        rows = cursor.fetchall()

        if rows:
            for row in rows:
                print(row)
        else:
            print("No books found in the database.")

        conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    check_books()
