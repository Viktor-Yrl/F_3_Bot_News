# Подключаем инструменты асинхронного выполнения
import asyncio

# Подключаем стандартный модуль журналирования
import logging

# Подключаем стандартный модуль для переменных окружения
import os

# Подключаем обработчик журналов с ротацией
from logging.handlers import RotatingFileHandler

# Подключаем библиотеку для запросов к NewsAPI
import requests

# Загружаем настройки из файла .env
from dotenv import load_dotenv

# Импортируем элементы интерфейса Telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

# Импортируем компоненты для запуска и управления ботом
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# Настраиваем вывод событий в терминал и файл bot.log
logging.basicConfig(
    # Указываем формат строки журнала
    format="%(asctime)s | %(levelname)s | %(message)s",

    # Записываем информационные сообщения и ошибки
    level=logging.INFO,

    # Указываем места сохранения журнала
    handlers=[
        # Записываем события в файл с ограниченным размером
        RotatingFileHandler(
            # Указываем имя основного файла
            "bot.log",

            # Ограничиваем один файл одним мегабайтом
            maxBytes=1_000_000,

            # Сохраняем три предыдущих файла
            backupCount=3,

            # Используем кодировку UTF-8
            encoding="utf-8",
        ),

        # Одновременно выводим события в терминал
        logging.StreamHandler(),
    ],
)

# Не записываем HTTP-запросы с токеном в журнал
logging.getLogger("httpx").setLevel(logging.WARNING)

# Создаём объект журнала для текущего файла
logger = logging.getLogger(__name__)

# Загружаем переменные из файла .env
load_dotenv()

# Получаем API-ключ NewsAPI
news_api_key = os.getenv("NEWS_API_KEY")

# Получаем токен Telegram-бота
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")

# Получаем разрешённый Chat ID из .env
allowed_chat_id_text = os.getenv("TELEGRAM_CHAT_ID")

# Проверяем наличие всех секретных настроек
if not news_api_key or not telegram_token or not allowed_chat_id_text:
    # Останавливаем программу при отсутствии настройки
    raise RuntimeError("Не все настройки найдены в .env")

# Преобразуем Chat ID из строки в число
allowed_chat_id = int(allowed_chat_id_text)


# Проверяем доступ текущего пользователя
def is_access_allowed(update: Update):
    # Получаем чат из обновления Telegram
    chat = update.effective_chat

    # Разрешаем доступ только нужному Chat ID
    return chat is not None and chat.id == allowed_chat_id


# Создаём собственную ошибку для ответов NewsAPI
class NewsAPIError(Exception):
    # Дополнительная логика пока не требуется
    pass

# Создаём главное меню
def create_main_menu():
    # Создаём строки с кнопками
    buttons = [
        # Кнопка перехода к источникам
        [InlineKeyboardButton(
            "Выбрать источник",
            callback_data="menu_sources",
        )],

        # Кнопка перехода к категориям
        [InlineKeyboardButton(
            "Выбрать категорию",
            callback_data="menu_categories",
        )],

        # Кнопка получения новостей
        [InlineKeyboardButton(
            "Получить новости",
            callback_data="get_news",
        )],
    ]

    # Превращаем список кнопок в Telegram-клавиатуру
    return InlineKeyboardMarkup(buttons)




# Обрабатываем команду /start
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    # Проверяем доступ пользователя
    if not is_access_allowed(update):
        # Записываем попытку доступа в журнал
        logger.warning(
            "Запрещённый доступ: chat_id=%s",
            update.effective_chat.id,
        )

        # Сообщаем пользователю об отказе
        await update.message.reply_text("Доступ запрещён.")

        # Прекращаем выполнение функции
        return

    # Отправляем приветствие и главное меню
    await update.message.reply_text(
     "Выберите способ получения новостей:\n\n"
        "Источник — новости конкретного канала.\n"
        "Категория — новости выбранной темы из СМИ США.",
        reply_markup=create_main_menu(),
    )


# Получаем статьи от NewsAPI
def get_articles(mode, value):
    # Сохраняем адрес NewsAPI
    news_url = "https://newsapi.org/v2/top-headlines"

    # Создаём общие параметры запроса
    news_params = {
        # Запрашиваем максимум шесть статей
        "pageSize": 6,

    }

    # Проверяем, выбран ли конкретный источник
    if mode == "source":
        # Добавляем источник, например CNN
        news_params["sources"] = value

    # Если выбрана категория
    else:
        # Ограничиваем источники США
        news_params["country"] = "us"

        # Добавляем категорию
        news_params["category"] = value

    # Отправляем запрос к NewsAPI
    response = requests.get(
        # Передаём адрес API
        news_url,

        # Передаём параметры запроса
        params=news_params,

        # Передаём API-ключ в защищённом HTTP-заголовке
        headers={"X-Api-Key": news_api_key},

        # Ограничиваем время ожидания
        timeout=10,
    )

    # Проверяем HTTP-ошибки
    response.raise_for_status()

    # Преобразуем JSON в словарь
    news_data = response.json()

    # Проверяем внутренний статус NewsAPI
    if news_data.get("status") != "ok":
        # Получаем описание ошибки
        error_message = news_data.get("message", "Неизвестная ошибка NewsAPI")

        # Передаём ошибку вызывающему коду
        raise NewsAPIError(error_message)

    # Возвращаем статьи или пустой список
    return news_data.get("articles", [])


# Обрабатываем нажатия на кнопки
async def handle_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    # Получаем информацию о нажатой кнопке
    query = update.callback_query

    # Проверяем доступ пользователя
    if not is_access_allowed(update):
        # Показываем уведомление об отказе
        await query.answer(
            "Доступ запрещён.",
            show_alert=True,
        )

        # Записываем попытку в журнал
        logger.warning(
            "Запрещённое нажатие: chat_id=%s",
            update.effective_chat.id,
        )

        # Прекращаем обработку кнопки
        return

    # Подтверждаем получение нажатия Telegram
    await query.answer()

    # Получаем служебное значение кнопки
    button_data = query.data

    # Проверяем нажатие кнопки источников
    if button_data == "menu_sources":
        # Создаём кнопки источников
        buttons = [
            # Первая строка источников
            [
                # Создаём кнопку ABC News
                InlineKeyboardButton(
                    "ABC News",
                    callback_data="source:abc-news",
                ),

                # Создаём кнопку CBS News
                InlineKeyboardButton(
                    "CBS News",
                    callback_data="source:cbs-news",
                ),
            ],

            # Вторая строка источников
            [
                # Создаём кнопку Fox News
                InlineKeyboardButton(
                    "Fox News",
                    callback_data="source:fox-news",
                ),

                # Создаём кнопку Politico
                InlineKeyboardButton(
                    "Politico",
                    callback_data="source:politico",
                ),
            ],

            # Третья строка источников
            [
                # Создаём кнопку NBC News
                InlineKeyboardButton(
                    "NBC News",
                    callback_data="source:nbc-news",
                ),

                # Создаём кнопку The Verge
                InlineKeyboardButton(
                    "The Verge",
                    callback_data="source:the-verge",
                ),
            ],

            # Четвёртая строка источников
            [
                # Создаём кнопку CNN
                InlineKeyboardButton(
                    "CNN",
                    callback_data="source:cnn",
                ),

                # Создаём кнопку BBC News
                InlineKeyboardButton(
                    "BBC News",
                    callback_data="source:bbc-news",
                ),
            ],

            # Последняя строка меню
            [
                # Создаём кнопку возврата в главное меню
                InlineKeyboardButton(
                    "Назад",
                    callback_data="back",
                ),
            ],
        ]

        # Заменяем сообщение меню списком источников
        await query.edit_message_text(
            "Выберите источник:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        # Завершаем обработку текущего нажатия
        return

    # Проверяем нажатие кнопки категорий
    if button_data == "menu_categories":
        # Создаём кнопки категорий
        buttons = [
            # Первая строка категорий
            [
                InlineKeyboardButton(
                    "Общие",
                    callback_data="category:general",
                ),
                InlineKeyboardButton(
                    "Бизнес",
                    callback_data="category:business",
                ),
            ],

            # Вторая строка категорий
            [
                InlineKeyboardButton(
                    "Технологии",
                    callback_data="category:technology",
                ),
                InlineKeyboardButton(
                    "Наука",
                    callback_data="category:science",
                ),
            ],

            # Третья строка категорий
            [
                InlineKeyboardButton(
                    "Спорт",
                    callback_data="category:sports",
                ),
                InlineKeyboardButton(
                    "Здоровье",
                    callback_data="category:health",
                ),
            ],

            # Кнопка возврата
            [
                InlineKeyboardButton(
                    "Назад",
                    callback_data="back",
                ),
            ],
        ]

        # Показываем список категорий
        await query.edit_message_text(
            "Выберите категорию:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        # Завершаем обработку
        return

    # Проверяем выбор источника
    if button_data.startswith("source:"):
        # Отделяем идентификатор источника
        source = button_data.split(":", 1)[1]

        # Запоминаем режим выбора
        context.user_data["mode"] = "source"

        # Запоминаем выбранный источник
        context.user_data["value"] = source

        # Показываем подтверждение
        await query.edit_message_text(
            f"Выбран источник: {source}",
            reply_markup=create_main_menu(),
        )

        # Завершаем обработку
        return

    # Проверяем выбор категории
    if button_data.startswith("category:"):
        # Отделяем название категории
        category = button_data.split(":", 1)[1]

        # Запоминаем режим выбора
        context.user_data["mode"] = "category"

        # Запоминаем выбранную категорию
        context.user_data["value"] = category

        # Показываем подтверждение
        await query.edit_message_text(
            f"Выбрана категория: {category}",
            reply_markup=create_main_menu(),
        )

        # Завершаем обработку
        return

    # Проверяем кнопку возврата
    if button_data == "back":
        # Возвращаем главное меню
        await query.edit_message_text(
            "Выберите источник или категорию:",
            reply_markup=create_main_menu(),
        )

        # Завершаем обработку
        return

    # Проверяем кнопку получения новостей
    if button_data == "get_news":
        # Получаем сохранённый режим или выбираем категорию по умолчанию
        mode = context.user_data.get("mode", "category")

        # Получаем сохранённое значение или общую категорию
        value = context.user_data.get("value", "general")

        # Показываем состояние загрузки
        await query.edit_message_text("Получаю новости...")

        # Пытаемся получить статьи
        try:
            # Выполняем синхронный запрос в отдельном потоке
            articles = await asyncio.to_thread(
                # Передаём вызываемую функцию
                get_articles,

                # Передаём режим поиска
                mode,

                # Передаём источник или категорию
                value,
            )

        # Перехватываем сетевую ошибку или ошибку ответа NewsAPI
        except (requests.RequestException, NewsAPIError):
            # Записываем подробности ошибки в bot.log
            logger.exception("Ошибка запроса к NewsAPI")

            # Показываем пользователю понятное сообщение
            await query.edit_message_text(
                "Не удалось получить новости. Попробуйте позже.",
                reply_markup=create_main_menu(),
            )

            # Прекращаем обработку
            return

        # Проверяем, вернулись ли статьи
        if not articles:
            # Записываем пустой результат в журнал
            logger.info(
                "Новости не найдены: mode=%s, value=%s",
                mode,
                value,
            )

            # Сообщаем пользователю об отсутствии статей
            await query.edit_message_text(
                "По выбранным параметрам новости не найдены.",
                reply_markup=create_main_menu(),
            )

            # Прекращаем обработку
            return

        # Перебираем полученные статьи
        for article in articles:
            # Получаем заголовок
            title = article.get("title") or "Без заголовка"

            # Получаем источник
            source = (
                article.get("source", {}).get("name")
                or "Неизвестный источник"
            )

            # Получаем ссылку
            article_url = article.get("url") or ""

            # Формируем сообщение
            message = (
                f"{title}\n\n"
                f"Источник: {source}\n"
                f"{article_url}"
            )

            # Отправляем статью в текущий чат
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text=message,
            )

        # Снова показываем главное меню
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text="Выберите следующее действие:",
            reply_markup=create_main_menu(),
        )

# Обрабатываем неожиданные ошибки Telegram-бота
async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    # Записываем техническую информацию в журнал
    logger.error(
        "Необработанная ошибка Telegram-бота",
        exc_info=context.error,
    )

    # Проверяем, что ошибка связана с обновлением Telegram
    if isinstance(update, Update) and update.effective_chat:
        # Пытаемся сообщить пользователю об ошибке
        try:
            # Отправляем сообщение в текущий чат
            await context.bot.send_message(
                # Передаём идентификатор текущего чата
                chat_id=update.effective_chat.id,

                # Передаём понятное сообщение пользователю
                text="Произошла внутренняя ошибка. Попробуйте ещё раз.",
            )

        # Перехватываем ошибку отправки уведомления
        except Exception:
            # Записываем её в журнал
            logger.exception("Не удалось сообщить пользователю об ошибке")

# Создаём и запускаем приложение
def main():
    # Создаём Telegram-приложение с токеном бота
    application = Application.builder().token(telegram_token).build()

    # Добавляем обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # Добавляем обработчик всех кнопок
    application.add_handler(CallbackQueryHandler(handle_button))

    # Подключаем общий обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем постоянное получение обновлений Telegram
    application.run_polling()


# Проверяем, что файл запущен напрямую
if __name__ == "__main__":
    # Запускаем основную функцию
    main()
