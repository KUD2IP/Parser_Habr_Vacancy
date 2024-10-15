import telebot
from telebot import types
import psycopg2
import time
from collections import defaultdict

TOKEN = '7277377935:AAG4QOl0WsSXwzqGLchrQ55kHuuHuqUT6d0'
bot = telebot.TeleBot(TOKEN)

DB_CONFIG = {
    'dbname': 'parserdb',
    'user': 'admin',
    'password': 'root',
    'host': 'localhost',
    'port': '5435'
}

user_states = {}


def get_vacancies(query, params):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        vacancies = cur.fetchall()
    except psycopg2.Error as e:
        print(f"Ошибка выполнения запроса к базе данных: {e}")
        return []
    cur.close()
    conn.close()
    return vacancies


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message,
                 "Приветствую, для более удобного взаимодействия с ботом, ознакомьтесь с командами."
                 "\n\nДля поиска введите название вакансии в поле ввода текста."
                 "\nИспользуйте /filters для настройки "
                 "фильтров."
                 "\nИспользуйте /stop для остановки отправки вакансий, а для возобновления /resume."
                 "\n\n*Для более удобного управления ботом используйте меню команд (три горизонтальные полоски слева от "
                 "поля ввода текста).*",
                 parse_mode='Markdown')


user_filters = {}


def set_city_filter(user_id, city):
    if user_id not in user_filters:
        user_filters[user_id] = {}
    user_filters[user_id]['city'] = city


def set_salary_filter(user_id, salary_from, salary_to):
    if user_id not in user_filters:
        user_filters[user_id] = {}
    user_filters[user_id]['salary_from'] = salary_from
    user_filters[user_id]['salary_to'] = salary_to


def set_filter(user_id, filter_name, *values):
    if user_id not in user_filters:
        user_filters[user_id] = {}
    if len(values) == 1:
        user_filters[user_id][filter_name] = values[0]
    else:
        user_filters[user_id][filter_name] = values


@bot.message_handler(commands=['filters'])
def vacancy_filters(message):
    markup = types.InlineKeyboardMarkup()
    itembtn1 = types.InlineKeyboardButton('По городу', callback_data='filter_city')
    itembtn2 = types.InlineKeyboardButton('По зарплате', callback_data='filter_salary')
    markup.add(itembtn1)
    markup.add(itembtn2)
    user_states[message.chat.id] = False
    bot.send_message(message.chat.id, "Выберите фильтр:", reply_markup=markup)


@bot.message_handler(commands=['resetfilters'])
def reset_filters(message):
    user_id = message.chat.id
    reset_user_filters(user_id)
    bot.send_message(user_id, "Все ваши фильтры были сброшены. Вы можете установить новые фильтры или начать поиск "
                              "вакансий без фильтров.")


def reset_user_filters(user_id):
    if user_id in user_filters:
        del user_filters[user_id]


@bot.callback_query_handler(func=lambda call: call.data.startswith('filter_'))
def handle_filters(call):
    # Получаем ID пользователя из коллбэка
    user_id = call.message.chat.id

    if call.data == 'filter_city':
        msg = bot.send_message(call.message.chat.id, "Введите город:")
        bot.register_next_step_handler(msg, set_city)
    elif call.data == 'filter_salary':
        msg = bot.send_message(user_id,
                               "Укажите интересующую зарплату в формате: МИН-МАКС (60000-120000)")
        bot.register_next_step_handler(msg, set_salary, user_id)
    bot.answer_callback_query(call.id)


def set_city(message):
    user_id = message.chat.id
    city = message.text
    set_city_filter(user_id, city)
    bot.send_message(user_id, f"Фильтр по городу установлен: {city}.\nУстановите ещё один фильтр, используя"
                              f" /filters или начните поиск, написав интересующее имя вакансии в поиск")


def set_salary(message, user_id):
    text = message.text.lower()
    salary_range = text.split('-')

    salary_from = ""
    salary_to = ""

    if len(salary_range) == 2:
        salary_from = salary_range[0].strip()
        salary_to = salary_range[1].strip()
    elif len(salary_range) == 1 and salary_range[0].isdigit():
        salary_from = salary_range[0].strip()
    else:
        bot.send_message(user_id, "Пожалуйста, укажите зарплату корректно.")
        return

    set_salary_filter(user_id, salary_from, salary_to)
    response_text = ("Фильтр по зарплате установлен.\nУстановите ещё один фильтр, используя /filters или начните поиск,"
                     "написав интересующее имя вакансии в поиск")
    if salary_from != "":
        response_text += f" От {salary_from}."
    if salary_to != "":
        response_text += f" До {salary_to}."
    bot.send_message(user_id, response_text)


@bot.message_handler(commands=['stop'])
def stop_sending(message):
    user_states[message.chat.id] = False
    bot.reply_to(message, "Отправка вакансий остановлена. Используйте команду /resume для возобновления.")


@bot.message_handler(commands=['resume'])
def resume_sending(message):
    user_states[message.chat.id] = True
    bot.reply_to(message, "Возобновление отправки вакансий. Пожалуйста, повторите ваш поиск.")


def generate_markdown_vacancy_message(vacancy):
    if len(vacancy) < 6:
        raise ValueError("Expected 6 values from the query result, got less. Received: {}".format(vacancy))
    name_vacancy, company_name, salary_ot, salary_do, city, url = vacancy

    salary = "не указано"
    if salary_ot != "" and salary_do != "":
        salary = f"от {salary_ot} до {salary_do}"
    elif salary_ot != "" and salary_do == "":
        salary = f"от {salary_ot}"

    return f"*{name_vacancy}*\nЗарплата: {salary}\nРаботодатель: {company_name}\nГород: {city}\nСсылка на вакансию: {url}"


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    search_text = message.text
    user_id = message.chat.id
    words = search_text.split()
    filters = user_filters.get(user_id, {})

    user_states[user_id] = True

    query_parts = [
        "SELECT name_vacancy, company_name, salary_ot, salary_do, city, url",
        "FROM vacancies",
    ]
    query_conditions = ["name_vacancy ILIKE %s" for word in words]
    query_parts.append("WHERE " + " AND ".join(query_conditions))

    params = ["%{}%".format(word.lower()) for word in words]

    if 'city' in filters:
        query_parts.append("AND city ILIKE %s")
        params.append("%" + filters['city'] + "%")
    if 'salary_from' in filters:
        query_parts.append("AND salary_ot >= %s")
        params.append("%" + filters['salary_from'] + "%")
    if 'salary_to' in filters:
        query_parts.append("AND salary_do <= %s")
        params.append("%" + filters['salary_to'] + "%")

    full_query = " ".join(query_parts)
    vacancies = get_vacancies(full_query, tuple(params))

    if vacancies:

        salary_message = f"Найдено вакансий: {len(vacancies)}\n"

        bot.send_message(user_id, salary_message)

        for vacancy in vacancies:
            if user_states.get(user_id, True):
                try:
                    bot.send_message(user_id, generate_markdown_vacancy_message(vacancy), parse_mode='Markdown')
                    time.sleep(1)
                except telebot.apihelper.ApiTelegramException as e:
                    if e.error_code == 429:
                        wait_time = e.result_json['parameters']['retry_after']
                        print(f"Слишком много запросов. Повторная отправка через {wait_time} секунд.")
                        time.sleep(wait_time)
                        bot.send_message(user_id, generate_markdown_vacancy_message(vacancy), parse_mode='Markdown')
            else:
                break
    else:
        bot.send_message(user_id, "По вашему запросу вакансии не найдены.")


bot.polling()
