FROM python:3.10

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

COPY bot.py /app/bot.py

CMD ["python", "bot.py"]