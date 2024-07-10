# Импорты
import requests
import json
import os
import sqlite3
import telegram
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Переменные окружения
load_dotenv()
TOKEN = os.getenv('TOKEN')
ADMIN_CHAT_ID = 808174847
# 808174847 м
# 6984945831 т

# Словари и списки для хранения данных
user_admin_chat = {}  # Словарь для хранения текущих запросов к администратору
active_dialogs = {}  # Словарь для хранения активных диалогов
message_history = {}  # Словарь для хранения истории сообщений
suggestions = {}  # Словарь для хранения предложений
anonymous_messages = []  # Список для хранения анонимных сообщений
is_recording_user = {}
is_recording_admin = False

# Файлы для сохранения данных
HISTORY_FILE = 'message_history.json'
ANON_FILE = 'anonymous_messages.json'
SUGGESTIONS_FILE = 'suggestions.json'

# Функции для работы с файлами
def load_message_history():
    global message_history
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as file:
                loaded_history = json.load(file)
                message_history = {int(key): value for key, value in loaded_history.items()}
                print("История сообщений загружена.")
        else:
            print(f"Файл {HISTORY_FILE} не найден.")
    except FileNotFoundError:
        print(f"Файл {HISTORY_FILE} не найден.")
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON в файле {HISTORY_FILE}: {e}")

# Сохранение истории сообщений
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
            with open(ANON_FILE, 'r', encoding='utf-8') as file:
                anonymous_messages = json.load(file)
                print("Анонимные сообщения загружены.")
        else:
            print(f"Файл {ANON_FILE} не найден.")
    except FileNotFoundError:
        print(f"Файл {ANON_FILE} не найден.")
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON в файле {ANON_FILE}: {e}")

# Сохранение анонимных сообщений
def save_anonymous_messages():
    try:
        with open(ANON_FILE, 'w', encoding='utf-8') as file:
            json.dump(anonymous_messages, file, ensure_ascii=False, indent=4)
        print("Анонимные сообщения сохранены.")
    except IOError as e:
        print(f"Ошибка при записи файла {ANON_FILE}: {e}")

def load_suggestions():
    global suggestions
    try:
        if os.path.exists(SUGGESTIONS_FILE):
            with open(SUGGESTIONS_FILE, 'r', encoding='utf-8') as file:
                loaded_suggestions = json.load(file)
                suggestions = {int(key): value for key, value in loaded_suggestions.items()}
                print("Предложения загружены.")
        else:
            print(f"Файл {SUGGESTIONS_FILE} не найден.")
    except FileNotFoundError:
        print(f"Файл {SUGGESTIONS_FILE} не найден.")
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON в файле {SUGGESTIONS_FILE}: {e}")

# Сохранение предложений
def save_suggestions():
    try:
        with open(SUGGESTIONS_FILE, 'w', encoding='utf-8') as file:
            json.dump({str(key): value for key, value in suggestions.items()}, file, ensure_ascii=False, indent=4)
        print("Предложения сохранены.")
    except IOError as e:
        print(f"Ошибка при записи файла {SUGGESTIONS_FILE}: {e}")




# Основные функции бота
async def start(update, context):
    user = update.effective_user

    # Остановить запись сообщений пользователя и администратора при старте
    await stop_recording_user(update, context)
    await stop_recording_admin(update, context)

    if not context.user_data.get('greeted', False):
        await send_welcome_message(update, context, user)
        context.user_data['greeted'] = True
    if not context.user_data.get('initialized'):
        context.user_data['initialized'] = True
        if user.id == ADMIN_CHAT_ID:
            await show_admin_menu(update, context)
        else:
            await show_main_menu(update, context)
    user = update.effective_user


async def send_welcome_message(update, context, user):
    welcome_text = (
        f"Привет, {user.first_name}! Я бот канала 'Good Books'.\n\n"
        f"Если у вас есть вопросы или предложения, обратитесь к администратору.\n"
        f"Администратор: @biblioteka_gb"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)

async def show_main_menu(update: Update, context: CallbackContext):
    buttons = [
        [InlineKeyboardButton("Предложка", callback_data='suggest')],
        [InlineKeyboardButton("Поиск книги", callback_data='search_book')],
        [InlineKeyboardButton("Сообщение администратору", callback_data='call_admin')],
        [InlineKeyboardButton("Анонимное предложение/жалоба", callback_data='anonymous_suggestion')],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text("Главное меню", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Главное меню", reply_markup=reply_markup)

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'suggest':
        await query.edit_message_text("Вы выбрали 'Предложение'. Отправьте ваше предложение.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]]))
        context.user_data['awaiting_suggestion'] = True

    elif query.data == 'call_admin':
        await query.edit_message_text("Администратор будет оповещен о вашем запросе. Пожалуйста, отправьте ваше сообщение.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]]))
        context.user_data['awaiting_admin_message'] = True
        active_dialogs[query.from_user.id] = True

    elif query.data == 'search_book':
        await query.edit_message_text("Вы выбрали 'Поиск книги'. Отправьте название книги для поиска.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]]))
        context.user_data['awaiting_search_query'] = True
        active_dialogs[query.from_user.id] = SEARCH_BOOK  # Добавлено отслеживание запроса поиска книги

    elif query.data == 'anonymous_suggestion':
        await query.edit_message_text("Вы выбрали 'Анонимное предложение/жалоба'. "
                                      "Отправьте ваше предложение или жалобу анонимно.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]]))
        context.user_data['awaiting_anonymous_suggestion'] = True

    elif query.data == 'show_active_dialogs':
        await show_active_dialogs(update, context)

    elif query.data == 'back_to_main_menu':
        context.user_data.clear()  # Очистить все состояния пользователя
        await show_main_menu(update, context)


async def handle_message(update: Update, context: CallbackContext):
    user = update.message.from_user
    text = update.message.text

    if user.id in active_dialogs and active_dialogs[user.id] == SEARCH_BOOK:
        await handle_search_query(update, context, text)
        return

    if user.id == ADMIN_CHAT_ID:
        await handle_admin_message(update, context)
        return

    if context.user_data.get('awaiting_search_query'):
        await handle_search_query(update, context, text)
        return

    if user.id in is_recording_user and is_recording_user[user.id]:
        if user.id not in message_history:
            message_history[user.id] = []
        message_history[user.id].append({"from": "user", "text": text})
        save_message_history()

    active_dialogs[user.id] = True

    if context.user_data.get('awaiting_suggestion'):
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"Новое предложение от пользователя @{user.username} (ID: {user.id}):\n{text}"
        )
        await update.message.reply_text("Спасибо за ваше предложение!")
        context.user_data['awaiting_suggestion'] = False

    elif context.user_data.get('awaiting_admin_message'):
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"Новое сообщение для админа от пользователя @{user.username} (ID: {user.id}):\n{text}"
        )
        await update.message.reply_text("Ваше сообщение отправлено администратору.")
        context.user_data['awaiting_admin_message'] = False

    elif context.user_data.get('awaiting_anonymous_suggestion'):
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"Анонимное предложение/жалоба:\n{text}"
        )
        await update.message.reply_text("Ваше сообщение отправлено анонимно.")
        context.user_data['awaiting_anonymous_suggestion'] = False

    else:
        await update.message.reply_text("Неизвестная команда. Пожалуйста, используйте меню для навигации.")

async def handle_search_query(update: Update, context: CallbackContext, query: str):
    books = search_books(query)
    if books:
        for index, book in enumerate(books, start=1):
            buttons = [
                [InlineKeyboardButton(f"Купить книгу {index}", url=f"tg://user?id={ADMIN_CHAT_ID}")]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            try:
                if book["image_url"]:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=book["image_url"],
                        caption=f"📚 {book['title']}\n💰 Цена: {book['price']}\n📦 Наличие: {book['availability']}",
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"{index}. 📚 {book['title']}\n💰 Цена: {book['price']}\n📦 Наличие: {book['availability']}\n(Фото отсутствует)",
                        reply_markup=reply_markup
                    )
            except telegram.error.BadRequest:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"{index}. 📚 {book['title']}\n💰 Цена: {book['price']}\n📦 Наличие: {book['availability']}\n(Фото не найдено)",
                    reply_markup=reply_markup
                )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Вернуться в главное меню",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]])
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Книги не найдены.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]])
        )
    active_dialogs[update.effective_chat.id] = False


async def handle_admin_message(update: Update, context: CallbackContext):
    user = update.message.from_user
    text = update.message.text

    if user.id == ADMIN_CHAT_ID:
        if text.startswith('/reply'):
            parts = text.split(' ', 2)
            if len(parts) < 3:
                await update.message.reply_text("Неправильный формат команды. Используйте: /reply <user_id> <сообщение>")
                return
            user_id = parts[1]
            reply_message = parts[2]

            try:
                user_id = int(user_id)
                user_chat = await context.bot.get_chat(user_id)
                if user_chat:
                    await context.bot.send_message(chat_id=user_id, text=f"Ответ от администратора:\n{reply_message}")
                    await update.message.reply_text(f"Сообщение отправлено пользователю {user_id} (ID: {user_id}).")

                    # Добавляем пользователя в список активных диалогов
                    active_dialogs[user_id] = True

                    # Сохраняем сообщение в историю только если запись включена
                    if is_recording_admin:
                        if user_id not in message_history:
                            message_history[user_id] = []
                        message_history[user_id].append({"from": "admin", "text": reply_message})
                        save_message_history()

                else:
                    await update.message.reply_text("Пользователь не найден.")

            except ValueError:
                await update.message.reply_text("Неправильный формат user_id. Должен быть числовым значением.")
            except Exception as e:
                await update.message.reply_text(f"Ошибка при отправке сообщения: {e}")
            return

        if context.user_data.get('awaiting_search_query'):
            await handle_search_query(update, context, text)
            return

    await update.message.reply_text("Неправильный формат команды. Используйте: /reply <user_id> <сообщение>")

    #--------

async def start_recording_user(update: Update, context: CallbackContext):
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        is_recording_user[user_id] = True

async def stop_recording_user(update: Update, context: CallbackContext):
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        if user_id in is_recording_user:
            is_recording_user[user_id] = False

async def start_recording_admin(update: Update, context: CallbackContext):
    global is_recording_admin
    is_recording_admin = True

async def stop_recording_admin(update: Update, context: CallbackContext):
    global is_recording_admin
    is_recording_admin = False

async def notify_admin(update: Update, context: CallbackContext):
    user = update.callback_query.from_user
    admin_message = (
        f"Пользователь @{user.username} ({user.id}) хочет связаться с администратором.\n"
        f"Имя пользователя: {user.first_name} {user.last_name or ''}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    user_admin_chat[user.id] = ADMIN_CHAT_ID
    active_dialogs[user.id] = True  # Добавляем пользователя в список активных диалогов



# Команды для администратора
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
        "/predl - Показать все предложения\n"
        "/clearpredl - Очистить все предложения\n"
        "/clearpredl <user_id> - Очистить историю предложений пользователя\n"
        "/reply <user_id> <сообщение>\n"
    )
    await update.message.reply_text(help_message)

async def show_admin_menu(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return
    keyboard = [
        [InlineKeyboardButton("Показать активные диалоги", callback_data='show_active_dialogs')],
        [InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Меню администратора:", reply_markup=reply_markup)

async def show_suggestions(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    if suggestions:
        suggestions_message = "\n\n".join([f"Пользователь {user_id} (@{suggestion['from']}): {suggestion['text']}"
                                           for user_id, user_suggestions in suggestions.items()
                                           for suggestion in user_suggestions])
        await update.message.reply_text(f"Предложения:\n{suggestions_message}")
    else:
        await update.message.reply_text("Предложений нет.")

async def clear_all_suggestions(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    suggestions.clear()
    save_suggestions()
    await update.message.reply_text("Все предложения очищены.")

async def clear_user_suggestions(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    try:
        user_id = int(context.args[0])
        if user_id in suggestions:
            del suggestions[user_id]
            save_suggestions()
            await update.message.reply_text(f"История предложений пользователя {user_id} очищена.")
        else:
            await update.message.reply_text("История предложений с этим пользователем не найдена.")
    except (IndexError, ValueError):
        await update.message.reply_text("Пожалуйста, укажите корректный ID пользователя.")



# Команды для администратора и операций с пользователями
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
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return
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
    await start(update, context)

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




    # Операции с анонимными сообщениями
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



SEARCH_BOOK = 1
# Операции с базой данных книг
def search_books(query):
    try:
        conn = sqlite3.connect('books.db')
        cursor = conn.cursor()

        formatted_query = f"%{query.upper()}%"

        cursor.execute("""
            SELECT id, title, price, image_url, availability
            FROM Book
            WHERE UPPER(title) LIKE ?
        """, (formatted_query,))

        rows = cursor.fetchall()

        books = []
        for row in rows:
            book = {
                "id": row[0],
                "title": row[1],
                "price": row[2],
                "image_url": row[3],
                "availability": row[4]
            }
            books.append(book)

        conn.close()
        return books
    except Exception as e:
        return []


# Основная функция запуска бота
def main():
    global message_history, active_dialogs
    load_message_history()  # Загружаем историю сообщений
    load_anonymous_messages()  # Загружаем анонимные сообщения
    load_suggestions()  # Загружаем предложения

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
    application.add_handler(CommandHandler("predl", show_suggestions))  # Команда для показа предложений
    application.add_handler(CommandHandler("clearpredl", clear_all_suggestions))  # Команда для очистки всех предложений
    application.add_handler(CommandHandler("clearpredl_user", clear_user_suggestions))  # Команда для очистки предложений пользователя
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & filters.User(ADMIN_CHAT_ID),
        handle_admin_message
    ))

    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.User(ADMIN_CHAT_ID),
        handle_message
    ))

    application.run_polling()


# Запуск приложения
if __name__ == '__main__':
    main()