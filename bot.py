import requests
import json
from telegram.ext import Updater
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
)
import os

TOKEN = '7012177270:AAHVn0WARbchPLZO1lmg4ixPv0HltXIO-ME'
API_URL = 'https://leolorenco.pythonanywhere.com/search'
ADMIN_CHAT_ID = 6984945831
user_admin_chat = {}  # Словарь для хранения текущих запросов к администратору
active_dialogs = {}  # Словарь для хранения активных диалогов
message_history = {}  # Словарь для хранения истории сообщений
anonymous_messages = []  # Список для хранения анонимных сообщений
HISTORY_FILE = 'message_history.json'
ANON_FILE = 'anonymous_messages.json'

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

def load_anonymous_messages():
    global anonymous_messages
    try:
        if os.path.exists(ANON_FILE):
            with open(ANON_FILE, 'r', encoding='utf-8-sig') as file:  # Используем 'utf-8-sig' для игнорирования BOM
                anonymous_messages = json.load(file)
                print("Анонимные сообщения загружены.")
        else:
            print(f"Файл {ANON_FILE} не найден.")
    except FileNotFoundError:
        print(f"Файл {ANON_FILE} не найден.")
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON в файле {ANON_FILE}: {e}")

def save_anonymous_messages():
    try:
        with open(ANON_FILE, 'w', encoding='utf-8') as file:
            json.dump(anonymous_messages, file, ensure_ascii=False, indent=4)
        print("Анонимные сообщения сохранены.")
    except IOError as e:
        print(f"Ошибка при записи файла {ANON_FILE}: {e}")

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

    # Добавляем кнопку для админа
    if user.id == ADMIN_CHAT_ID:
        keyboard.append([InlineKeyboardButton("Показать активные диалоги", callback_data='show_active_dialogs')])

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
        user_id = query.from_user.id
        active_dialogs[user_id] = True  # Устанавливаем диалог как активный

    elif query.data == 'search_book':
        await query.edit_message_text("Вы выбрали 'Поиск книги'. Отправьте название книги для поиска.")
        context.user_data['awaiting_search_query'] = True

    elif query.data == 'anonymous_suggestion':
        await query.edit_message_text("Вы выбрали 'Анонимное предложение/жалоба'. "
                                      "Отправьте ваше предложение или жалобу анонимно.")
        context.user_data['awaiting_anonymous_suggestion'] = True

    elif query.data == 'show_active_dialogs':
        await show_active_dialogs(update, context)

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
            anonymous_messages.append(anonymous_suggestion)
            save_anonymous_messages()
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Новое анонимное сообщение: {anonymous_suggestion}")
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
                active_dialogs[user_id] = True  # Устанавливаем диалог как активный

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
                active_dialogs[user_id] = True  # Устанавливаем диалог как активный
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
        "/users - Показать всех пользователей\n"
        "/history <user_id> - Показать историю сообщений с пользователем\n"
        "/closedia <user_id> - Закрыть диалог с пользователем\n"
        "/clearchat <user_id> - Очистить историю сообщений с пользователем\n"
        "/anon - Показать анонимные сообщения\n"
        "/clearanonall - Очистить все анонимные сообщения\n"
        "/clearanon <номер> - Удалить одно анонимное сообщение по номеру\n"
    )
    await update.message.reply_text(help_message)

async def show_users(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    active_users_message = "Активные пользователи:\n"
    inactive_users_message = "Неактивные пользователи:\n"

    for user_id in message_history.keys():
        user_info = await context.bot.get_chat(user_id)
        username = f"@{user_info.username}" if user_info.username else user_info.first_name

        if active_dialogs.get(user_id, False):
            active_users_message += f"ID: {user_id}, Username: {username}\n"
        else:
            inactive_users_message += f"ID: {user_id}, Username: {username}\n"

    users_message = active_users_message + "\n" + "*"*10 + "\n" + inactive_users_message
    await update.message.reply_text(users_message)

async def show_user_history(update: Update, context: CallbackContext):
    try:
        user_id = int(context.args[0])
        if user_id in message_history:
            history = message_history[user_id]
            user_info = await context.bot.get_chat(user_id)
            username = f"@{user_info.username}" if user_info.username else ""
            history_message = f"История сообщений с пользователем {user_id} ({username}):\n"
            for message in history:
                sender = "Админ" if message['from'] == 'admin' else "Пользователь"
                history_message += f"{sender}: {message['text']}\n"
            await update.message.reply_text(history_message)
        else:
            await update.message.reply_text("История сообщений с этим пользователем пуста.")
    except (IndexError, ValueError):
        await update.message.reply_text("Пожалуйста, укажите корректный ID пользователя.")

async def show_active_dialogs(update: Update, context: CallbackContext):
    if update.callback_query.from_user.id != ADMIN_CHAT_ID:
        await update.callback_query.message.reply_text("Эта команда доступна только для администратора.")
        return

    active_users_message = "Активные диалоги:\n"
    for user_id in active_dialogs:
        user_info = await context.bot.get_chat(user_id)
        username = f"@{user_info.username}" if user_info.username else user_info.first_name
        active_users_message += f"ID: {user_id}, Username: {username}\n"

    await update.callback_query.message.reply_text(active_users_message)

async def close_dialog(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    try:
        user_id = int(context.args[0])
        if user_id in active_dialogs:
            active_dialogs[user_id] = False
            await update.message.reply_text(f"Диалог с пользователем {user_id} закрыт.")
        else:
            await update.message.reply_text("Этот диалог уже закрыт или не существует.")
    except (IndexError, ValueError):
        await update.message.reply_text("Пожалуйста, укажите корректный ID пользователя.")

async def clear_chat(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    try:
        user_id = int(context.args[0])
        if user_id in message_history:
            del message_history[user_id]
            save_message_history()
            await update.message.reply_text(f"История сообщений с пользователем {user_id} очищена.")
        else:
            await update.message.reply_text("История сообщений с этим пользователем не найдена.")
    except (IndexError, ValueError):
        await update.message.reply_text("Пожалуйста, укажите корректный ID пользователя.")

async def show_anonymous_messages(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    if anonymous_messages:
        anon_messages = "\n\n".join([f"{index + 1}. {msg}" for index, msg in enumerate(anonymous_messages)])
        await update.message.reply_text(f"Анонимные сообщения:\n{anon_messages}")
    else:
        await update.message.reply_text("Анонимных сообщений нет.")

async def clear_anonymous_messages(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    anonymous_messages.clear()
    save_anonymous_messages()
    await update.message.reply_text("Все анонимные сообщения очищены.")

async def clear_one_anonymous_message(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    try:
        message_index = int(context.args[0]) - 1
        if 0 <= message_index < len(anonymous_messages):
            del anonymous_messages[message_index]
            save_anonymous_messages()
            await update.message.reply_text(f"Сообщение номер {message_index + 1} удалено.")
        else:
            await update.message.reply_text("Неверный номер сообщения.")
    except (IndexError, ValueError):
        await update.message.reply_text("Пожалуйста, укажите корректный номер сообщения.")

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
    load_anonymous_messages()  # Загружаем анонимные сообщения

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(CommandHandler("users", show_users))
    application.add_handler(CommandHandler("history", show_user_history))
    application.add_handler(CommandHandler("closedia", close_dialog))
    application.add_handler(CommandHandler("clearchat", clear_chat))  # Добавляем команду clearchat
    application.add_handler(CommandHandler("anon", show_anonymous_messages))  # Команда для показа анонимных сообщений
    application.add_handler(CommandHandler("clearanonall", clear_anonymous_messages))  # Команда для очистки всех анонимных сообщений
    application.add_handler(CommandHandler("clearanon", clear_one_anonymous_message))  # Команда для удаления одного анонимного сообщения
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