import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
)
import os

TOKEN = '7012177270:AAHVn0WARbchPLZO1lmg4ixPv0HltXIO-ME'
API_URL = 'https://leolorenco.pythonanywhere.com/search'
ADMIN_CHAT_ID = 808174847
user_admin_chat = {}  # Словарь для хранения текущих запросов к администратору
message_history = {}  # Словарь для хранения истории сообщений
HISTORY_FILE = 'message_history.json'

def load_message_history():
    global message_history
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as file:
                loaded_history = json.load(file)
                for key, value in loaded_history.items():
                    message_history[int(key)] = value
                print("История сообщений загружена.")
        else:
            print(f"Файл {HISTORY_FILE} не найден.")
    except FileNotFoundError:
        print(f"Файл {HISTORY_FILE} не найден.")
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON в файле {HISTORY_FILE}: {e}")

def save_message_history():
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as file:
            json.dump({str(key): value for key, value in message_history.items()}, file, ensure_ascii=False, indent=4)
        print("История сообщений сохранена.")
    except IOError as e:
        print(f"Ошибка при записи файла {HISTORY_FILE}: {e}")

async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот канала 'Книги Books'.\n\n"
        f"Если у вас есть вопросы или предложения, обратитесь к администратору.\n"
        f"Администратор: @biblioteka_gb"
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

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'suggest':
        await query.edit_message_text("Вы выбрали 'Предложка'. Отправьте ваше предложение.")
        context.user_data['awaiting_suggestion'] = True

    elif query.data == 'call_admin':
        await query.edit_message_text("Администратор будет оповещен о вашем запросе.")
        await notify_admin(update, context)

    elif query.data == 'search_book':
        await query.edit_message_text("Вы выбрали 'Поиск книги'. Отправьте название книги для поиска.")
        context.user_data['awaiting_search_query'] = True

    elif query.data == 'anonymous_suggestion':
        await query.edit_message_text("Вы выбрали 'Анонимное предложение/жалоба'. "
                                      "Отправьте ваше предложение или жалобу анонимно.")
        context.user_data['awaiting_anonymous_suggestion'] = True

async def handle_message(update: Update, context: CallbackContext):
    if update.message.chat.type == update.message.chat.PRIVATE:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.username or update.message.from_user.first_name

        if context.user_data.get('awaiting_search_query'):
            search_query = update.message.text.strip()
            books = search_books(search_query)
            if books:
                message = "\n\n".join([f"{book['title']} - {book['author']} - {book['genre']}" for book in books])
            else:
                message = "Книги не найдены."
            await update.message.reply_text(message)
            del context.user_data['awaiting_search_query']

        elif context.user_data.get('awaiting_suggestion'):
            suggestion = update.message.text.strip()
            await update.message.reply_text("Ваше предложение отправлено.")
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Предложение от @{user_name} ({user_id}): {suggestion}")
            del context.user_data['awaiting_suggestion']

        elif context.user_data.get('awaiting_anonymous_suggestion'):
            anonymous_suggestion = update.message.text.strip()
            await update.message.reply_text("Ваше предложение или жалоба отправлены анонимно.")
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Анонимное предложение/жалоба: {anonymous_suggestion}")
            del context.user_data['awaiting_anonymous_suggestion']

        else:
            if user_id in user_admin_chat:
                # Проверяем, существует ли уже запись для данного пользователя
                if user_id not in message_history:
                    message_history[user_id] = []

                # Сохранение сообщения в истории
                message_history[user_id].append({'from': 'user', 'text': update.message.text})
                save_message_history()  # Сохраняем историю в файл

                await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Сообщение от @{user_name} ({user_id}): {update.message.text}")

async def handle_admin_message(update: Update, context: CallbackContext):
    if update.message.chat.type == update.message.chat.PRIVATE and update.message.from_user.id == ADMIN_CHAT_ID:
        message_parts = update.message.text.split(maxsplit=1)
        if len(message_parts) == 2:
            try:
                user_id = int(message_parts[0])
                reply_message = message_parts[1]

                # Проверяем, существует ли уже запись для данного пользователя
                if user_id not in message_history:
                    message_history[user_id] = []

                # Сохранение сообщения в истории
                message_history[user_id].append({'from': 'admin', 'text': reply_message})
                save_message_history()  # Сохраняем историю в файл

                await context.bot.send_message(chat_id=user_id, text=reply_message)
            except ValueError:
                await update.message.reply_text("Пожалуйста, укажите корректный ID пользователя и сообщение.")
        else:
            await update.message.reply_text("Пожалуйста, укажите ID пользователя и сообщение.")

async def notify_admin(update: Update, context: CallbackContext):
    user = update.callback_query.from_user
    admin_message = (
        f"Пользователь @{user.username} ({user.id}) хочет связаться с администратором.\n"
        f"Имя пользователя: {user.first_name} {user.last_name or ''}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    user_admin_chat[user.id] = ADMIN_CHAT_ID

async def show_help(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    help_message = (
        "Команды для администратора:\n"
        "/help - Показать это сообщение\n"
        "/users - Показать список пользователей, которые связались с администратором\n"
        "/history <user_id> - Показать историю сообщений пользователя\n\n"
        "Чтобы ответить пользователю, отправьте сообщение в формате:\n"
        "<user_id> <сообщение>\n"
        "где user_id - это идентификатор пользователя, а сообщение - ваш ответ."
    )
    await update.message.reply_text(help_message)

async def show_users(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    if user_admin_chat:
        users_message = "Список пользователей, которые связались с администратором:\n"
        for user_id, admin_id in user_admin_chat.items():
            user_info = await context.bot.get_chat(user_id)
            users_message += f"ID: {user_id}, Username: @{user_info.username or user_info.first_name}\n"
        await update.message.reply_text(users_message)
    else:
        await update.message.reply_text("Нет пользователей, которые связались с администратором.")

async def show_user_history(update: Update, context: CallbackContext):
    try:
        user_id = int(context.args[0])
        if user_id in message_history:
            history = message_history[user_id]
            user_info = await context.bot.get_chat(user_id)
            username =f"@{user_info.username}" if user_info.username else ""
            history_message = f"История сообщений с пользователем {user_id} ({username}):\n"
            for message in history:
                sender = "Админ" if message['from'] == 'admin' else "Пользователь"
                history_message += f"{sender}: {message['text']}\n"
            await update.message.reply_text(history_message)
        else:
            await update.message.reply_text("История сообщений с этим пользователем пуста.")
    except (IndexError, ValueError):
        await update.message.reply_text("Пожалуйста, укажите корректный ID пользователя.")

def search_books(query):
    try:
        response = requests.get(API_URL, params={'query': query})
        response.raise_for_status()
        books = response.json().get('books', [])
        return books
    except requests.exceptions.RequestException as e:
        print(f"Error fetching books: {e}")
        return []

def main():
    global message_history
    load_message_history()  # Загружаем историю сообщений

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(CommandHandler("users", show_users))
    application.add_handler(CommandHandler("history", show_user_history))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.User(ADMIN_CHAT_ID), 
        handle_message
    ))
    
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & filters.User(ADMIN_CHAT_ID), 
        handle_admin_message
    ))

    application.run_polling()

if __name__ == '__main__':
    main()