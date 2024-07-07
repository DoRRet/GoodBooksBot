import requests
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = '7012177270:AAHVn0WARbchPLZO1lmg4ixPv0HltXIO-ME'
API_URL = 'https://leolorenco.pythonanywhere.com/search'

# Функция обработки команды /start
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот канала 'Книги Books'.\n\n"
        f"Если у вас есть вопросы или предложения, обратитесь к администратору.\n"
        f"Администратор: @admin_books"
    )
    keyboard = [
        [
            InlineKeyboardButton("Предложка", callback_data='suggest'),
            InlineKeyboardButton("Позвать админа", callback_data='call_admin'),
        ],
        [
            InlineKeyboardButton("Поиск книги", callback_data='search_book'),
            InlineKeyboardButton("Анонимное предложение/жалоба", callback_data='anonymous_suggestion'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите нужную опцию:', reply_markup=reply_markup)

# Функция для обработки нажатий кнопок
async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'suggest':
        await query.edit_message_text("Вы выбрали 'Предложка'. Отправьте ваше предложение.")
        # Здесь можно обработать предложку

    elif query.data == 'call_admin':
        await query.edit_message_text("Администратор будет оповещен о вашем запросе.")
        # Здесь можно добавить логику для оповещения админа

    elif query.data == 'search_book':
        await query.edit_message_text("Вы выбрали 'Поиск книги'. Отправьте название книги для поиска.")
        context.user_data['awaiting_search_query'] = True
        return

    elif query.data == 'anonymous_suggestion':
        await query.edit_message_text("Вы выбрали 'Анонимное предложение/жалоба'. "
                                      "Отправьте ваше предложение или жалобу анонимно.")
        # Здесь можно обработать анонимное предложение или жалобу

# Функция для обработки сообщений с текстом
async def handle_message(update: Update, context: CallbackContext):
    if 'awaiting_search_query' in context.user_data and context.user_data['awaiting_search_query']:
        search_query = update.message.text.strip()
        books = search_books(search_query)
        if books:
            message = "\n\n".join([f"{book['title']} - {book['author']} - {book['genre']}" for book in books])
        else:
            message = "Книги не найдены."
        await update.message.reply_text(message)
        del context.user_data['awaiting_search_query']

# Функция для поиска книг по запросу в вашем Flask приложении на PythonAnywhere
def search_books(query):
    try:
        response = requests.get(API_URL, params={'query': query})
        response.raise_for_status()  # Это выбросит исключение для кода состояния HTTP 4xx/5xx
        books = response.json().get('books', [])
        return books
    except requests.exceptions.RequestException as e:
        print(f"Error fetching books: {e}")
        return []

# Основная функция для запуска бота
def main():
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд и сообщений
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()