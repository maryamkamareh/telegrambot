import sqlite3
import telebot
import logging
from requests.exceptions import ReadTimeout

# # تنظیمات logging
# logging.basicConfig(level=logging.DEBUG)

bot = telebot.TeleBot("6703251131:AAEZ16FtXpPgONduJkas8hkK7WkEOzE3Tuo")

# متغیرهای وضعیت
user_states = {}
user_data = {}

# فرم‌ها
form_peyroshyar = [
    "نام و نام خانوادگی",
    "شماره دانشجویی",
    "رشته و گرایش",
    "اخرین مدرک تحصیلی",
    "کد ملی",
    "ادرس ایمیل",
    "تلفن همراه",
    "تاریخ تولد",
    "محل تولد",
    "مقطع تحصیلی",
    "دانشگاه و واحد دانشگاهی",
    "نام و نام خانوادگی استاد راهنما",
    "ایمیل استاد راهنما",
]

form_irandoc = [
    "نام و نام خانوادگی",
    "نام پدر",
    "تاریخ تولد",
    "شماره ملی",
    "شماره تماس",
    "شماره دانشجوئی",
    "رشته",
    "گرایش",
    "دانشگاه/ واحد",
    "نام و نام خانوادگی استاد راهنما",
    "ایمیل استاد راهنما"
]

# دکمه‌های تعاملی
first_button = telebot.types.InlineKeyboardButton("اطلاعات لازم جهت ثبت نام پژوهشیار", callback_data="peyroshyar")
second_button = telebot.types.InlineKeyboardButton("اطلاعات لازم جهت ثبت نام های ایرانداک", callback_data="irandoc")
markup = telebot.types.InlineKeyboardMarkup(row_width=1)
markup.add(first_button, second_button)


# اتصال به دیتابیس و ایجاد جداول
def init_db():
    conn = sqlite3.connect('user.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS peyroshyar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT,
                    student_id TEXT,
                    field TEXT,
                    last_degree TEXT,
                    national_code TEXT,
                    email TEXT,
                    phone TEXT,
                    birth_date TEXT,
                    birth_place TEXT,
                    education_level TEXT,
                    university TEXT,
                    advisor_name TEXT,
                    advisor_email TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS irandoc (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT,
                    father_name TEXT,
                    birth_date TEXT,
                    national_code TEXT,
                    phone TEXT,
                    student_id TEXT,
                    field TEXT,
                    specialization TEXT,
                    university TEXT,
                    advisor_name TEXT,
                    advisor_email TEXT
                )''')
    conn.commit()
    conn.close()


# ذخیره اطلاعات در دیتابیس
def save_to_db(user_id, form, data):
    conn = sqlite3.connect('user.db')
    c = conn.cursor()

    if form == "peyroshyar":
        c.execute('''INSERT INTO peyroshyar (user_id, name, student_id, field, last_degree, national_code, email, phone, birth_date, birth_place, education_level, university, advisor_name, advisor_email)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, *data))
    elif form == "irandoc":
        c.execute('''INSERT INTO irandoc (user_id, name, father_name, birth_date, national_code, phone, student_id, field, specialization, university, advisor_name, advisor_email)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, *data))

    conn.commit()
    conn.close()


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "سلام، لطفا یکی از گزینه های زیر را برای ثبت اطلاعات انتخاب کنید:",
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "peyroshyar":
        user_states[call.from_user.id] = ("peyroshyar", 0)
        user_data[call.from_user.id] = []
        bot.send_message(call.message.chat.id, form_peyroshyar[0])
    elif call.data == "irandoc":
        user_states[call.from_user.id] = ("irandoc", 0)
        user_data[call.from_user.id] = []
        bot.send_message(call.message.chat.id, form_irandoc[0])


@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def handle_message(message):
    user_id = message.from_user.id
    state, question_index = user_states[user_id]

    if state == "peyroshyar":
        form = form_peyroshyar
    else:
        form = form_irandoc

    # ذخیره پاسخ کاربر
    user_data[user_id].append(message.text)

    # پرسیدن سوال بعدی
    question_index += 1
    if question_index < len(form):
        user_states[user_id] = (state, question_index)
        bot.send_message(message.chat.id, form[question_index])
    else:
        # فرم کامل شد
        bot.send_message(message.chat.id, "اطلاعات شما با موفقیت ثبت شد.")
        # ذخیره اطلاعات در دیتابیس
        try:
            save_to_db(user_id, state, user_data[user_id])
        except Exception as e:
            logging.error(f"An error occurred while saving to the database: {e}")
        del user_states[user_id]
        del user_data[user_id]


# شروع ربات و ایجاد جداول در دیتابیس
init_db()

# مدیریت تایم‌اوت‌ها و خطاهای احتمالی
try:
    bot.infinity_polling()
except ReadTimeout:
    logging.error("A read timeout occurred during polling")
except Exception as e:
    logging.error(f"An unexpected error occurred: {e}")
