# Подключаем стандартный модуль для работы с переменными окружения
import os

# Подключаем библиотеку для выполнения HTTP-запросов
import requests

# Импортируем функцию загрузки переменных из файла .env
from dotenv import load_dotenv


# Загружаем переменные из файла .env
load_dotenv()

# Получаем токен Telegram-бота из переменной окружения
token = os.getenv("TELEGRAM_BOT_TOKEN")

# Проверяем, найден ли токен
if not token:
    # Останавливаем программу, если токен отсутствует
    raise RuntimeError("TELEGRAM_BOT_TOKEN не найден")

# Формируем адрес метода getUpdates Telegram Bot API
# Этот метод возвращает сообщения, отправленные боту
url = f"https://api.telegram.org/bot{token}/getUpdates"

# Отправляем GET-запрос и ждём ответ не более 10 секунд
response = requests.get(url, timeout=10)

# Вызываем исключение, если Telegram вернул HTTP-ошибку
response.raise_for_status()

# Преобразуем JSON-ответ Telegram в словарь Python
data = response.json()

# Получаем из ответа список обновлений и сообщений
updates = data["result"]

# Проверяем, есть ли сообщения в списке
if not updates:
    # Останавливаем программу, если пользователь ещё не написал боту
    raise RuntimeError("Сообщения не найдены. Отправьте боту /start")

# Перебираем все полученные обновления
for update in updates:
    # Пытаемся получить сообщение из текущего обновления
    message = update.get("message")

    # Проверяем, что обновление действительно содержит сообщение
    if message:
        # Получаем идентификатор чата и выводим его в терминал
        print("Chat ID:", message["chat"]["id"])
