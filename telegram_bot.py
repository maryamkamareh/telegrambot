import logging
import re
from datetime import datetime

import requests
import telebot
from requests.exceptions import ReadTimeout

# تنظیمات logging
logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot("6703251131:AAEZ16FtXpPgONduJkas8hkK7WkEOzE3Tuo")

# متغیرهای وضعیت
user_states = {}
user_data = {}

# فرم‌ها
form_peyroshyar = [
    "نام و نام خانوادگی",
    "شماره دانشجویی",
    "رشته و گرایش",
    "آخرین مدرک تحصیلی",
    "کد ملی",
    "آدرس ایمیل",
    "تلفن همراه: (شماره حتما فعال، در دسترس و به نام دانشجو باشد.)",
    "سال تولد",
    "ماه تولد",
    "روز تولد",
    "محل تولد",
    "مقطع تحصیلی",
    "دانشگاه",
    "واحد دانشگاهی",
    "نام و نام خانوادگی کامل استاد راهنما",
    "ایمیل استاد راهنما",
]

form_irandoc = [
    "نام و نام خانوادگی",
    "نام پدر",
    "سال تولد",
    "ماه تولد",
    "روز تولد",
    "کد ملی",
    "تلفن همراه: (شماره حتما فعال، در دسترس و به نام دانشجو باشد.)",
    "شماره دانشجویی",
    "رشته",
    "گرایش",
    "دانشگاه",
    "واحد دانشگاهی",
    "نام و نام خانوادگی کامل استاد راهنما",
    "ایمیل استاد راهنما"
]

# دکمه‌های تعاملی
first_button = telebot.types.InlineKeyboardButton("اطلاعات لازم جهت ثبت نام پژوهشیار", callback_data="peyroshyar")
second_button = telebot.types.InlineKeyboardButton("اطلاعات لازم جهت ثبت نام های ایرانداک", callback_data="irandoc")
markup = telebot.types.InlineKeyboardMarkup(row_width=1)
markup.add(first_button, second_button)


def generate_degree_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    degrees = ["کارشناسی", "کارشناسی ارشد", "دکتری"]
    for degree in degrees:
        markup.add(telebot.types.InlineKeyboardButton(degree, callback_data=f"degree_{degree}"))
    return markup


def generate_month_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
    buttons = [telebot.types.InlineKeyboardButton(month, callback_data=f"month_{month}") for month in months]
    for i in range(0, len(buttons), 3):
        markup.add(*buttons[i:i + 3])
    return markup


def generate_day_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=7)
    days = [str(day) for day in range(1, 32)]
    buttons = [telebot.types.InlineKeyboardButton(day, callback_data=f"month_{day}") for day in days]
    for i in range(0, len(buttons), 7):
        markup.add(*buttons[i:i + 7])
    return markup


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id,
                     "دانشجوی گرامی؛ لطفا اطلاعات خواسته شده در لینک را با دقت پر کنید. توجه داشته باشید هرگونه بی دقتی در ثبت اطلاعات باعث اختلال در ثبت نام و در نتیجه به تعویق افتادن روند امور دانشگاهی شما می شود.، لطفا یکی از گزینه های زیر را برای ثبت اطلاعات انتخاب کنید:",
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    if call.data == "peyroshyar":
        user_states[user_id] = ("peyroshyar", 0)
        bot.send_message(call.message.chat.id, form_peyroshyar[0])
    elif call.data == "irandoc":
        user_states[user_id] = ("irandoc", 0)
        bot.send_message(call.message.chat.id, form_irandoc[0])
    elif call.data.startswith("degree_"):
        degree = call.data.split("_")[1]
        state, question_index = user_states[user_id]
        if state == "peyroshyar":
            form = form_peyroshyar
        else:
            form = form_irandoc
        user_data[user_id][form[question_index]] = degree
        user_states[user_id] = (state, question_index + 1)
        ask_next_question(call.message.chat.id, user_id)
    elif call.data.startswith("month_"):
        month = call.data.split("_")[1]
        state, question_index = user_states[user_id]
        if state == "peyroshyar":
            form = form_peyroshyar
        else:
            form = form_irandoc
        user_data[user_id][form[question_index]] = month
        user_states[user_id] = (state, question_index + 1)
        ask_next_question(call.message.chat.id, user_id)
    elif call.data.startswith("day_"):
        day = call.data.split("_")[1]
        state, question_index = user_states[user_id]
        if state == "peyroshyar":
            form = form_peyroshyar
        else:
            form = form_irandoc
        user_data[user_id][form[question_index]] = day
        user_states[user_id] = (state, question_index + 1)
        ask_next_question(call.message.chat.id, user_id)


@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def handle_message(message):
    user_id = message.from_user.id
    state, question_index = user_states[user_id]

    if state == "peyroshyar":
        form = form_peyroshyar
    else:
        form = form_irandoc

    current_question = form[question_index]

    # بررسی صحت شماره دانشجویی
    if current_question == "شماره دانشجویی" and not message.text.isdigit():
        bot.send_message(message.chat.id, "شماره دانشجویی باید فقط شامل اعداد باشد. لطفاً دوباره وارد کنید:")
        return

    # بررسی صحت کد ملی
    if current_question == "کد ملی" and (not message.text.isdigit() or len(message.text) != 10):
        bot.send_message(message.chat.id, "کد ملی باید 10 رقم باشد. لطفاً دوباره وارد کنید:")
        return

    # بررسی صحت ایمیل
    if current_question == "آدرس ایمیل" and not re.match(r"[^@]+@[^@]+\.[^@]+", message.text):
        bot.send_message(message.chat.id, "فرمت ایمیل صحیح نیست. لطفاً دوباره وارد کنید:")
        return

    # بررسی صحت شماره تماس
    if current_question == "تلفن همراه: (شماره حتما فعال، در دسترس و به نام دانشجو باشد.)" and (
            not message.text.isdigit() or len(message.text) != 11):
        bot.send_message(message.chat.id, "شماره تماس باید 11 رقم باشد. لطفاً دوباره وارد کنید:")
        return

    # بررسی صحت ایمیل استاد راهنما
    if current_question == "ایمیل استاد راهنما" and not re.match(r"[^@]+@[^@]+\.[^@]+", message.text):
        bot.send_message(message.chat.id, "فرمت ایمیل صحیح نیست. لطفاً دوباره وارد کنید:")
        return

    # بررسی صحت سال تولد
    if current_question == "سال تولد":
        if not message.text.isdigit() or int(message.text) < 1300 or int(message.text) > 1500:
            bot.send_message(message.chat.id, "سال تولد باید عددی بین 1300 تا 1500 باشد. لطفاً دوباره وارد کنید:")
            return

    # ذخیره پاسخ کاربر
    user_data[user_id][current_question] = message.text

    if should_show_inline_keyboard(current_question, user_id):
        return

    # پرسیدن سوال بعدی
    user_states[user_id] = (state, question_index + 1)
    ask_next_question(message.chat.id, user_id)


def ask_next_question(chat_id, user_id):
    state, question_index = user_states[user_id]

    if state == "peyroshyar":
        form = form_peyroshyar
    else:
        form = form_irandoc

    if question_index < len(form):
        current_question = form[question_index]
        if not should_show_inline_keyboard(current_question, user_id):
            bot.send_message(chat_id, current_question)
    else:
        submit_form(user_id, state, chat_id)


def should_show_inline_keyboard(question, user_id):
    if question == "آخرین مدرک تحصیلی":
        bot.send_message(user_id, "لطفاً آخرین مدرک تحصیلی خود را انتخاب کنید:", reply_markup=generate_degree_markup())
        return True
    if question == "مقطع تحصیلی":
        bot.send_message(user_id, "لطفاً مقطع تحصیلی خود را انتخاب کنید:", reply_markup=generate_degree_markup())
        return True
    if question == "ماه تولد":
        bot.send_message(user_id, "لطفاً ماه تولد خود را انتخاب کنید:", reply_markup=generate_month_markup())
        return True
    if question == "روز تولد":
        bot.send_message(user_id, "لطفاً روز تولد خود را انتخاب کنید:", reply_markup=generate_day_markup())
        return True
    return False


def submit_form(user_id, state, chat_id):
    if state == "peyroshyar":
        required_fields = [
            'نام و نام خانوادگی', 'شماره دانشجویی', 'رشته و گرایش', 'آخرین مدرک تحصیلی', 'کد ملی', 'آدرس ایمیل',
            'تلفن همراه: (شماره حتما فعال، در دسترس و به نام دانشجو باشد.)', 'سال تولد', 'ماه تولد', 'روز تولد',
            'محل تولد', 'مقطع تحصیلی', 'دانشگاه', 'واحد دانشگاهی',
            'نام و نام خانوادگی کامل استاد راهنما', 'ایمیل استاد راهنما'
        ]
    else:
        required_fields = [
            'نام و نام خانوادگی', 'نام پدر', 'سال تولد', 'ماه تولد', 'روز تولد', 'کد ملی',
            'تلفن همراه: (شماره حتما فعال، در دسترس و به نام دانشجو باشد.)',
            'شماره دانشجویی', 'رشته', 'گرایش', 'دانشگاه', 'واحد دانشگاهی', 'نام و نام خانوادگی کامل استاد راهنما',
            'ایمیل استاد راهنما'
        ]

    missing_fields = [field for field in required_fields if field not in user_data[user_id]]

    if missing_fields:
        bot.send_message(chat_id, f"لطفاً اطلاعات زیر را تکمیل کنید: {', '.join(missing_fields)}")
        return
    if state == "peyroshyar":
        data = {
            'name': user_data[user_id]['نام و نام خانوادگی'],
            'student_id': user_data[user_id]['شماره دانشجویی'],
            'field': user_data[user_id]['رشته و گرایش'],
            'last_degree': user_data[user_id]['آخرین مدرک تحصیلی'],
            'national_code': user_data[user_id]['کد ملی'],
            'email': user_data[user_id]['آدرس ایمیل'],
            'phone': user_data[user_id]['تلفن همراه: (شماره حتما فعال، در دسترس و به نام دانشجو باشد.)'],
            'birth_year': user_data[user_id]['سال تولد'],
            'birth_month': user_data[user_id]['ماه تولد'],
            'birth_day': user_data[user_id]['روز تولد'],
            'birth_place': user_data[user_id]['محل تولد'],
            'education_level': user_data[user_id]['مقطع تحصیلی'],
            'university': user_data[user_id]['دانشگاه'],
            'university_stage': user_data[user_id]['واحد دانشگاهی'],
            'advisor_name': user_data[user_id]['نام و نام خانوادگی کامل استاد راهنما'],
            'advisor_email': user_data[user_id]['ایمیل استاد راهنما'],
        }
        url = 'http://rouyeshme.ir/api/research_registers/'
    else:
        data = {
            'name': user_data[user_id]['نام و نام خانوادگی'],
            'father_name': user_data[user_id]['نام پدر'],
            'birth_year': user_data[user_id]['سال تولد'],
            'birth_month': user_data[user_id]['ماه تولد'],
            'birth_day': user_data[user_id]['روز تولد'],
            'national_code': user_data[user_id]['کد ملی'],
            'phone': user_data[user_id]['تلفن همراه: (شماره حتما فعال، در دسترس و به نام دانشجو باشد.)'],
            'student_id': user_data[user_id]['شماره دانشجویی'],
            'field': user_data[user_id]['رشته'],
            'specialization': user_data[user_id]['گرایش'],
            'university': user_data[user_id]['دانشگاه'],
            'university_stage': user_data[user_id]['واحد دانشگاهی'],
            'advisor_name': user_data[user_id]['نام و نام خانوادگی کامل استاد راهنما'],
            'advisor_email': user_data[user_id]['ایمیل استاد راهنما'],
        }
        url = 'http://rouyeshme.ir/api/irandoc_registers/'

    response = requests.post(url, data=data)
    if response.status_code == 201:
        bot.send_message(chat_id,
                         "اطلاعات شما با موفقیت ثبت شد. موسسه آموزشی و پژوهشی رویش از همکاری با شما صمیمانه سپاسگزار است.")
    else:
        bot.send_message(chat_id, "خطایی رخ داده است. لطفاً دوباره تلاش کنید.")
        logging.error(f"Error {response.status_code}: {response.text}")

    # پاک کردن داده‌های کاربر
    del user_states[user_id]
    del user_data[user_id]


def validate_date_format(date_string):
    try:
        datetime.strptime(date_string, '%d/%m/%Y')
        return True
    except ValueError:
        return False


# مدیریت تایم‌اوت‌ها و خطاهای احتمالی
try:
    bot.infinity_polling()
except ReadTimeout:
    logging.error("A read timeout occurred during polling")
except Exception as e:
    logging.error(f"An unexpected error occurred: {e}")
