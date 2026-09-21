import sqlite3
import telebot
from telebot import types

TOKEN = "8717281063:AAEaqhe-A1ErkfvL0oqLMYSI1SVsj5fXNPE"

OWNER_IDS = [8544964652]

bot = telebot.TeleBot(TOKEN)
conn = sqlite3.connect("library.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
               CREATE TABLE IF NOT EXISTS books
               (
                   id
                   INTEGER
                   PRIMARY
                   KEY
                   AUTOINCREMENT,
                   title
                   TEXT
                   NOT
                   NULL,
                   author
                   TEXT,
                   year
                   INTEGER,
                   available
                   INTEGER
                   DEFAULT
                   1
               )
               """)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users
    (
        id
        INTEGER
        PRIMARY
        KEY
        AUTOINCREMENT,
        telegram_id
        INTEGER
        UNIQUE,
        full_name
        TEXT,
        username
        TEXT
    )
    """)
cursor.execute("""
               CREATE TABLE IF NOT EXISTS rentals
               (
                   id
                   INTEGER
                   PRIMARY
                   KEY
                   AUTOINCREMENT,
                   book_id
                   INTEGER,
                   telegram_id
                   INTEGER,
                   returned
                   INTEGER
                   DEFAULT
                   0
               )
               """)
cursor.execute("""
               CREATE TABLE IF NOT EXISTS admins
               (
                   id
                   INTEGER
                   PRIMARY
                   KEY
                   AUTOINCREMENT,
                   telegram_id
                   INTEGER
                   UNIQUE,
                   full_name
                   TEXT,
                   username
                   TEXT
               )
               """)
conn.commit()


def is_owner(telegram_id):
    return telegram_id in OWNER_IDS


def is_admin(telegram_id):
    if telegram_id in OWNER_IDS:
        return True
    cursor.execute("SELECT id FROM admins WHERE telegram_id=?", (telegram_id,))
    return cursor.fetchone() is not None


def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("Kitob qo'shish"),
        types.KeyboardButton("Kitobni tahrirlash"),
        types.KeyboardButton("Kitobni o'chirish"),
        types.KeyboardButton("Kitob qidirish"),
        types.KeyboardButton("Ijaraga olish"),
        types.KeyboardButton("Kitobni qaytarish"),
    )
    return markup


def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("Kitob qo'shish"),
        types.KeyboardButton("Kitobni tahrirlash"),
        types.KeyboardButton("Kitobni o'chirish"),
        types.KeyboardButton("Kitob qidirish"),
        types.KeyboardButton("Ijaraga olish"),
        types.KeyboardButton("Kitobni qaytarish"),
        types.KeyboardButton("Admin panel"),
    )
    return markup


def get_menu(telegram_id):
    return admin_menu() if is_admin(telegram_id) else main_menu()


def admin_panel_menu(telegram_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("Barcha foydalanuvchilar"),
        types.KeyboardButton("Barcha kitoblar"),
        types.KeyboardButton("Ijaradagi kitoblar"),
        types.KeyboardButton("Statistika"),
    )
    if is_owner(telegram_id):
        markup.add(
            types.KeyboardButton("Admin qo'shish"),
            types.KeyboardButton("Admin o'chirish"),
        )
    markup.add(
        types.KeyboardButton("Adminlar"),
        types.KeyboardButton("Orqaga"),
    )
    return markup


def save_user(message):
    user = message.from_user
    cursor.execute("SELECT id FROM users WHERE telegram_id=?", (user.id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (telegram_id, full_name, username) VALUES (?, ?, ?)",
            (user.id, user.full_name, user.username),
        )
        conn.commit()


def format_book(row):
    book_id, title, author, year, available = row
    holat = "Mavjud" if available else "Band (ijarada)"
    return f"ID: {book_id}\nNomi: {title}\nMuallif: {author}\nYil: {year}\nHolati: {holat}"


def find_books(query):
    like = f"%{query}%"
    cursor.execute(
        "SELECT id, title, author, year, available FROM books WHERE title LIKE ? OR author LIKE ?",
        (like, like),
    )
    return cursor.fetchall()


@bot.message_handler(commands=["start"])
def start(message):
    save_user(message)
    bot.send_message(
        message.chat.id,
        """Kutubxona boshqaruv boti

Kitob qo'shish - Kutubxonaga yangi kitoblarni kiritish.
Kitobni tahrirlash - Mavjud kitob ma'lumotlarini yangilash.
Kitobni o'chirish - Keraksiz yoki mavjud bo'lmagan kitoblarni bazadan o'chirish.
Kitob qidirish - Nomi, muallifi yoki boshqa ma'lumotlari bo'yicha kitoblarni tezkor qidirish.
Ijaraga olish - Kitobni ijaraga olish va holatini yangilash.
Kitobni qaytarish - Qaytarilgan kitobni kutubxona fondiga tiklash.""",
        reply_markup=get_menu(message.from_user.id),
    )


@bot.message_handler(func=lambda m: m.text == "Kitob qo'shish")
def add_book_start(message):
    msg = bot.send_message(message.chat.id, "Kitob nomini kiriting:")
    bot.register_next_step_handler(msg, add_book_title)


def add_book_title(message):
    title = message.text.strip()
    msg = bot.send_message(message.chat.id, "Muallifini kiriting:")
    bot.register_next_step_handler(msg, add_book_author, title)


def add_book_author(message, title):
    author = message.text.strip()
    msg = bot.send_message(message.chat.id, "Nashr yilini kiriting (masalan: 1990):")
    bot.register_next_step_handler(msg, add_book_year, title, author)


def add_book_year(message, title, author):
    try:
        year = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Yil raqam bo'lishi kerak. Qaytadan urinib ko'ring.",
                         reply_markup=get_menu(message.from_user.id))
        return
    cursor.execute(
        "INSERT INTO books (title, author, year, available) VALUES (?, ?, ?, 1)",
        (title, author, year),
    )
    conn.commit()
    bot.send_message(message.chat.id, f"Kitob qo'shildi:\n\n{title}\n{author}\n{year}",
                     reply_markup=get_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Kitobni tahrirlash")
def edit_book_start(message):
    msg = bot.send_message(message.chat.id, "Tahrirlamoqchi bo'lgan kitob nomi yoki muallifini kiriting:")
    bot.register_next_step_handler(msg, edit_book_search)


def edit_book_search(message):
    results = find_books(message.text.strip())
    if not results:
        bot.send_message(message.chat.id, "Hech narsa topilmadi.", reply_markup=get_menu(message.from_user.id))
        return
    text = "\n\n".join(format_book(r) for r in results)
    msg = bot.send_message(message.chat.id, f"Topilgan kitoblar:\n\n{text}\n\nTahrirlash uchun kitob ID sini kiriting:")
    bot.register_next_step_handler(msg, edit_book_choose)


def edit_book_choose(message):
    try:
        book_id = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "ID raqam bo'lishi kerak.", reply_markup=get_menu(message.from_user.id))
        return
    cursor.execute("SELECT id FROM books WHERE id=?", (book_id,))
    if cursor.fetchone() is None:
        bot.send_message(message.chat.id, "Bunday ID topilmadi.", reply_markup=get_menu(message.from_user.id))
        return
    msg = bot.send_message(
        message.chat.id,
        "Yangi ma'lumotlarni vergul bilan kiriting:\nNomi, Muallif, Yil\n\nMasalan: O'tkan kunlar, Abdulla Qodiriy, 1926",
    )
    bot.register_next_step_handler(msg, edit_book_apply, book_id)


def edit_book_apply(message, book_id):
    parts = [p.strip() for p in message.text.split(",")]
    if len(parts) != 3:
        bot.send_message(message.chat.id, "Format noto'g'ri. Qaytadan urinib ko'ring.",
                         reply_markup=get_menu(message.from_user.id))
        return
    title, author, year_text = parts
    try:
        year = int(year_text)
    except ValueError:
        bot.send_message(message.chat.id, "Yil raqam bo'lishi kerak.", reply_markup=get_menu(message.from_user.id))
        return
    cursor.execute(
        "UPDATE books SET title=?, author=?, year=? WHERE id=?",
        (title, author, year, book_id),
    )
    conn.commit()
    bot.send_message(message.chat.id, "Kitob ma'lumotlari yangilandi.", reply_markup=get_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Kitobni o'chirish")
def delete_book_start(message):
    msg = bot.send_message(message.chat.id, "O'chirmoqchi bo'lgan kitob nomi yoki muallifini kiriting:")
    bot.register_next_step_handler(msg, delete_book_search)


def delete_book_search(message):
    results = find_books(message.text.strip())
    if not results:
        bot.send_message(message.chat.id, "Hech narsa topilmadi.", reply_markup=get_menu(message.from_user.id))
        return
    text = " ".join(format_book(r) for r in results)
    msg = bot.send_message(message.chat.id, f"Topilgan kitoblar:\n\n{text}\n\nO'chirish uchun kitob ID sini kiriting:")
    bot.register_next_step_handler(msg, delete_book_apply)


def delete_book_apply(message):
    try:
        book_id = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "ID raqam bo'lishi kerak.", reply_markup=get_menu(message.from_user.id))
        return
    cursor.execute("SELECT id FROM books WHERE id=?", (book_id,))
    if cursor.fetchone() is None:
        bot.send_message(message.chat.id, "Bunday ID topilmadi.", reply_markup=get_menu(message.from_user.id))
        return
    cursor.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    bot.send_message(message.chat.id, "Kitob o'chirildi.", reply_markup=get_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Kitob qidirish")
def search_book_start(message):
    msg = bot.send_message(message.chat.id, "Qidiruv uchun kitob nomi yoki muallifini kiriting:")
    bot.register_next_step_handler(msg, search_book_apply)


def search_book_apply(message):
    results = find_books(message.text.strip())
    if not results:
        bot.send_message(message.chat.id, "Hech narsa topilmadi.", reply_markup=get_menu(message.from_user.id))
        return
    text = "\n\n".join(format_book(r) for r in results)
    bot.send_message(message.chat.id, f"Topilgan kitoblar:\n\n{text}", reply_markup=get_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Ijaraga olish")
def rent_book_start(message):
    msg = bot.send_message(message.chat.id, "Ijaraga olmoqchi bo'lgan kitob nomi yoki muallifini kiriting:")
    bot.register_next_step_handler(msg, rent_book_search)


def rent_book_search(message):
    results = find_books(message.text.strip())
    if not results:
        bot.send_message(message.chat.id, "Hech narsa topilmadi.", reply_markup=get_menu(message.from_user.id))
        return
    text = "\n\n".join(format_book(r) for r in results)
    msg = bot.send_message(message.chat.id,
                           f"Topilgan kitoblar:\n\n{text}\n\nIjaraga olish uchun kitob ID sini kiriting:")
    bot.register_next_step_handler(msg, rent_book_apply)


def rent_book_apply(message):
    try:
        book_id = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "ID raqam bo'lishi kerak.", reply_markup=get_menu(message.from_user.id))
        return
    cursor.execute("SELECT available FROM books WHERE id=?", (book_id,))
    row = cursor.fetchone()
    if row is None:
        bot.send_message(message.chat.id, "Bunday ID topilmadi.", reply_markup=get_menu(message.from_user.id))
        return
    if row[0] == 0:
        bot.send_message(message.chat.id, "Bu kitob hozir band (ijarada).", reply_markup=get_menu(message.from_user.id))
        return
    save_user(message)
    cursor.execute("UPDATE books SET available=0 WHERE id=?", (book_id,))
    cursor.execute(
        "INSERT INTO rentals (book_id, telegram_id) VALUES (?, ?)",
        (book_id, message.from_user.id),
    )
    conn.commit()
    bot.send_message(message.chat.id, "Kitob muvaffaqiyatli ijaraga olindi.",
                     reply_markup=get_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Kitobni qaytarish")
def return_book_start(message):
    cursor.execute("""

                   SELECT books.id, books.title, books.author, books.year
                   FROM rentals
                            JOIN books ON books.id = rentals.book_id
                   WHERE rentals.telegram_id = ?
                     AND rentals.returned = 0
                   """,
                   (message.from_user.id,),
                   )
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(message.chat.id, "Sizda hozircha qaytarilmagan kitoblar yo'q.",
                         reply_markup=get_menu(message.from_user.id))
        return
    text = "\n\n".join(f"ID: {r[0]}\n{r[1]}\n{r[2]}\n{r[3]}" for r in rows)
    msg = bot.send_message(message.chat.id, f"Sizdagi kitoblar:\n\n{text}\n\nQaytarish uchun kitob ID sini kiriting:")
    bot.register_next_step_handler(msg, return_book_apply)


def return_book_apply(message):
    try:
        book_id = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "ID raqam bo'lishi kerak.", reply_markup=get_menu(message.from_user.id))
        return
    cursor.execute(
        "SELECT id FROM rentals WHERE book_id=? AND telegram_id=? AND returned=0",
        (book_id, message.from_user.id),
    )
    rental = cursor.fetchone()
    if rental is None:
        bot.send_message(message.chat.id, "Bu kitob sizda ijarada emas.", reply_markup=get_menu(message.from_user.id))
        return
    cursor.execute(
        "UPDATE rentals SET returned=1 WHERE id=?",
        (rental[0],),
    )
    cursor.execute("UPDATE books SET available=1 WHERE id=?", (book_id,))
    conn.commit()
    bot.send_message(message.chat.id, "Kitob muvaffaqiyatli qaytarildi.", reply_markup=get_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Admin panel")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "Sizda ruxsat yo'q.", reply_markup=get_menu(message.from_user.id))
        return
    bot.send_message(message.chat.id, "Admin panel:", reply_markup=admin_panel_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Orqaga")
def admin_back(message):
    bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=get_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Barcha foydalanuvchilar")
def admin_all_users(message):
    if not is_admin(message.from_user.id):
        return
    cursor.execute("SELECT telegram_id, full_name, username FROM users ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(message.chat.id, "Foydalanuvchilar yo'q.", reply_markup=admin_panel_menu(message.from_user.id))
        return
    lines = []
    for tg_id, full_name, username in rows:
        uname = f"@{username}" if username else "username yo'q"
        lines.append(f"ID: {tg_id}\nIsm: {full_name}\nUsername: {uname}")
    text = "\n\n".join(lines)
    for i in range(0, len(text), 3500):
        bot.send_message(message.chat.id, text[i:i + 3500])
    bot.send_message(message.chat.id, f"Jami foydalanuvchilar: {len(rows)}",
                     reply_markup=admin_panel_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Barcha kitoblar")
def admin_all_books(message):
    if not is_admin(message.from_user.id):
        return
    cursor.execute("SELECT id, title, author, year, available FROM books ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(message.chat.id, "Kitoblar yo'q.", reply_markup=admin_panel_menu(message.from_user.id))
        return
    text = "\n\n".join(format_book(r) for r in rows)
    for i in range(0, len(text), 3500):
        bot.send_message(message.chat.id, text[i:i + 3500])
    bot.send_message(message.chat.id, f"Jami kitoblar: {len(rows)}",
                     reply_markup=admin_panel_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Ijaradagi kitoblar")
def admin_active_rentals(message):
    if not is_admin(message.from_user.id):
        return
    cursor.execute("""
                   SELECT books.id, books.title, books.author, rentals.telegram_id, users.full_name
                   FROM rentals
                            JOIN books ON books.id = rentals.book_id
                            LEFT JOIN users ON users.telegram_id = rentals.telegram_id
                   WHERE rentals.returned = 0
                   ORDER BY rentals.id
                   """)

    rows = cursor.fetchall()
    if not rows:
        bot.send_message(message.chat.id, "Hozir ijarada kitob yo'q.",
                         reply_markup=admin_panel_menu(message.from_user.id))
        return
    lines = []
    for book_id, title, author, tg_id, full_name in rows:
        lines.append(
            f"Kitob ID: {book_id}\n{title} ({author})\nOluvchi: {full_name or tg_id} (ID: {tg_id})"
        )
    text = "\n\n".join(lines)
    for i in range(0, len(text), 3500):
        bot.send_message(message.chat.id, text[i:i + 3500])
    bot.send_message(message.chat.id, f"Jami ijaradagi kitoblar: {len(rows)}",
                     reply_markup=admin_panel_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Statistika")
def admin_stats(message):
    if not is_admin(message.from_user.id):
        return
    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM books WHERE available=1")
    available_books = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM books WHERE available=0")
    rented_books = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM rentals")
    total_rentals = cursor.fetchone()[0]
    text = (
        f"Statistika:\n\n"
        f"Jami kitoblar: {total_books}\n"
        f"Mavjud kitoblar: {available_books}\n"
        f"Ijaradagi kitoblar: {rented_books}\n"
        f"Jami foydalanuvchilar: {total_users}\n"
        f"Jami ijara amallari: {total_rentals}"
    )
    bot.send_message(message.chat.id, text, reply_markup=admin_panel_menu(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "Admin qo'shish")
def add_admin_start(message):
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "Bu amal faqat bosh admin uchun.",
                         reply_markup=admin_panel_menu(message.from_user.id))
        return
    msg = bot.send_message(message.chat.id,
                           "Yangi admin qilmoqchi bo'lgan foydalanuvchining Telegram ID raqamini yuboring:\n\n(Foydalanuvchi avval botga /start bosgan bo'lishi kerak)")
    bot.register_next_step_handler(msg, add_admin_apply)


def add_admin_apply(message):
    if not is_owner(message.from_user.id):
        return
    try:
        new_admin_id = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "ID raqam bo'lishi kerak.",
                         reply_markup=admin_panel_menu(message.from_user.id))
        return

    if is_admin(new_admin_id):
        bot.send_message(message.chat.id, "Bu foydalanuvchi allaqachon admin.",
                         reply_markup=admin_panel_menu(message.from_user.id))
        return

    cursor.execute("SELECT full_name, username FROM users WHERE telegram_id=?", (new_admin_id,))
    row = cursor.fetchone()
    full_name = row[0] if row else None
    username = row[1] if row else None

    cursor.execute(
        "INSERT INTO admins (telegram_id, full_name, username) VALUES (?, ?, ?)",
        (new_admin_id, full_name, username),
    )
    conn.commit()
    bot.send_message(message.chat.id, f"Foydalanuvchi (ID: {new_admin_id}) admin etib tayinlandi.",
                     reply_markup=admin_panel_menu(message.from_user.id))

    try:
        bot.send_message(new_admin_id, "Tabriklaymiz! Sizga admin huquqlari berildi.",
                         reply_markup=get_menu(new_admin_id))
    except Exception:
        pass


@bot.message_handler(func=lambda m: m.text == "Admin o'chirish")
def remove_admin_start(message):
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "Bu amal faqat bosh admin uchun.",
                         reply_markup=admin_panel_menu(message.from_user.id))
        return
    cursor.execute("SELECT telegram_id, full_name, username FROM admins ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(message.chat.id, "Hozircha qo'shilgan adminlar yo'q.",
                         reply_markup=admin_panel_menu(message.from_user.id))
        return
    lines = []
    for tg_id, full_name, username in rows:
        uname = f"@{username}" if username else "username yo'q"
        lines.append(f"ID: {tg_id}\nIsm: {full_name}\n{uname}")
    text = "\n\n".join(lines)
    msg = bot.send_message(message.chat.id,
                           f"Adminlar ro'yxati:\n\n{text}\n\nO'chirmoqchi bo'lgan adminning Telegram ID sini kiriting:")
    bot.register_next_step_handler(msg, remove_admin_apply)


def remove_admin_apply(message):
    if not is_owner(message.from_user.id):
        return
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "ID raqam bo'lishi kerak.",
                         reply_markup=admin_panel_menu(message.from_user.id))
        return

    if is_owner(admin_id):
        bot.send_message(message.chat.id, "Bosh adminni o'chirib bo'lmaydi.",
                         reply_markup=admin_panel_menu(message.from_user.id))
        return

    cursor.execute("SELECT id FROM admins WHERE telegram_id=?", (admin_id,))
    if cursor.fetchone() is None:
        bot.send_message(message.chat.id, "Bunday admin topilmadi.",
                         reply_markup=admin_panel_menu(message.from_user.id))
        return

    cursor.execute("DELETE FROM admins WHERE telegram_id=?", (admin_id,))
    conn.commit()
    bot.send_message(message.chat.id, f"Admin (ID: {admin_id}) o'chirildi.",
                     reply_markup=admin_panel_menu(message.from_user.id))

    try:
        bot.send_message(admin_id, "Sizning admin huquqlaringiz bekor qilindi.", reply_markup=get_menu(admin_id))
    except Exception:
        pass


@bot.message_handler(func=lambda m: m.text == "Adminlar")
def list_admins(message):
    if not is_admin(message.from_user.id):
        return
    lines = []
    for owner_id in OWNER_IDS:
        lines.append(f"ID: {owner_id}\n(Bosh admin)")
    cursor.execute("SELECT telegram_id, full_name, username FROM admins ORDER BY id")
    rows = cursor.fetchall()
    for tg_id, full_name, username in rows:
        uname = f"@{username}" if username else "username yo'q"
        lines.append(f"ID: {tg_id}\nIsm: {full_name or '-'}\n{uname}")
    text = "\n\n".join(lines)
    bot.send_message(message.chat.id, f"Adminlar ro'yxati:\n\n{text}\n\nJami: {len(lines)}",
                     reply_markup=admin_panel_menu(message.from_user.id))


@bot.message_handler(func=lambda m: True)
def unknown(message):
    save_user(message)
    bot.send_message(message.chat.id, "Menyudan kerakli bo'limni tanlang:", reply_markup=get_menu(message.from_user.id))

print("Asadni boti ishga tushdi xatoliklari bo'lsa uzur")
bot.infinity_polling()