# Подключаем стандартный модуль для работы с переменными окружения
import os

# Подключаем библиотеку для выполнения HTTP-запросов
import requests

# Импортируем функцию загрузки переменных из файла .env
from dotenv import load_dotenv


# Загружаем переменные окружения из файла .env
load_dotenv()

# Получаем секретный токен Telegram-бота
token = os.getenv("TELEGRAM_BOT_TOKEN")

# Получаем идентификатор чата, куда нужно отправить сообщение
chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Проверяем наличие токена и идентификатора чата
if not token or not chat_id:
    # Останавливаем программу, если хотя бы одно значение отсутствует
    raise RuntimeError("Токен или Chat ID не найден в .env")

# Формируем адрес метода sendMessage в Telegram Bot API
url = f"https://api.telegram.org/bot{token}/sendMessage"

# Формируем данные отправляемого сообщения
data = {
    # Указываем чат, в который нужно отправить сообщение
    "chat_id": chat_id,

    # Указываем текст сообщения
    "text": "Тестовое сообщение от новостного бота",
}

# Отправляем POST-запрос в Telegram и ждём не более 10 секунд
response = requests.post(url, data=data, timeout=10)

# Вызываем исключение, если Telegram вернул HTTP-ошибку
response.raise_for_status()

# Преобразуем JSON-ответ Telegram в словарь Python
result = response.json()

# Проверяем внутренний статус выполнения запроса Telegram
if not result["ok"]:
    # Останавливаем программу и выводим ответ при ошибке
    raise RuntimeError(result)

# Сообщаем в терминале об успешной отправке
print("Сообщение успешно отправлено")
