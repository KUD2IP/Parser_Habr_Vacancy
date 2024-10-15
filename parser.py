from datetime import time

import psycopg2
import requests
import schedule
from bs4 import BeautifulSoup

DB_CONFIG = {
    'dbname': 'parserdb',
    'user': 'admin',
    'password': 'root',
    'host': 'localhost',
    'port': '5435'
}


def save_to_db(id, company, vacancies, salary_from, salary_to, city, url):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except TypeError as e:
        print(f"Ошибка типа: {e}")
        return
    cur = conn.cursor()
    vacancies_id = id
    name_vacancy = vacancies
    company_names = company
    salary_ot = salary_from
    salary_do = salary_to
    cities = city
    urls = url

    insert_query = """
            INSERT INTO vacancies (vacancies_id, name_vacancy, company_name, salary_ot, salary_do, city, url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (vacancies_id) DO NOTHING;
            """
    cur.execute(insert_query, (
        vacancies_id, name_vacancy, company_names, salary_ot, salary_do, cities, urls))
    conn.commit()


def parsing_habr():
    page = 1
    id = 1

    while True:
        url = f"https://career.habr.com/vacancies?page={page}&type=all"

        response = requests.get(url)

        soup = BeautifulSoup(response.text, 'html.parser')

        # if soup.find("div", {"class": "vacancy-card"}) is None:
        #     break

        for link in soup.find_all("div", {"class": "vacancy-card__inner"}):
            company_name = link.find("a", {"class": "link-comp link-comp--appearance-dark"}).text
            vacancy_name = link.find("a", {"class": "vacancy-card__title-link"}).text
            salary = link.find("div", {"class": "basic-salary"}).text
            salary_from = ""
            salary_to = ""
            city = link.find("div", {"class": "vacancy-card__meta"})
            cities = ""
            href_url = link.find("a", {"class": "vacancy-card__icon-link"}).attrs["href"]
            urls = "https://career.habr.com" + href_url

            for i in city.find_all("a", {"class": "link-comp link-comp--appearance-dark"}):
                cities += i.text + " "

            if salary == "":
                salary_to = "не указано"

            elif "от" and "до" in salary:
                str = salary.replace(" ", "").replace("от", "").replace("до", " ")[:-1]
                s = str.split(" ")
                salary_from = s[0]
                salary_to = s[1]

            elif "от" in salary and "до" not in salary:
                str = salary.replace("от", "").replace(" ", "")[:-1]
                salary_from = str

            elif "до" in salary and "от" not in salary:
                str = salary.replace("до", "").replace(" ", "")[:-1]
                salary_to = str

            save_to_db(id, company_name, vacancy_name, salary_from, salary_to, cities, urls)
            id += 1
        page += 1


if __name__ == '__main__':
    schedule.every(3).days.at("00:00").do(parsing_habr())
    while True:
        schedule.run_pending()
        time.sleep(60)
