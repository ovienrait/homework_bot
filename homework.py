import os
import requests
import time
import logging

from logging import StreamHandler
from http import HTTPStatus
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import TokenError, ResponseError

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
handler = StreamHandler()
logger.addHandler(handler)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Функция для проверки переменных окружения."""
    logging.info('Проверка наличия переменных окружения.')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def get_api_answer(timestamp):
    """Функция для отправки запроса к API."""
    logging.info('Отправление запроса к API.')
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            raise ResponseError('Ошибка запроса!')
        return response.json()
    except requests.RequestException:
        raise ResponseError('Ошибка запроса!')


def check_response(response):
    """Функция для проверки ответа от API."""
    logging.info('Проверка ответа API.')
    if 'homeworks' in response:
        logging.info('Ответ от API получен.')
    elif response['code'] == 'UnknownError':
        logging.critical('Неверно указан временной промежуток!')
    elif response['code'] == 'not_authenticated':
        logging.critical('Токен авторизации недействителен!')
    if not isinstance(response['homeworks'], list):
        raise TypeError


def parse_status(homework):
    """Функция для формирования сообщения."""
    logging.info('Проверка статуса домашней работы.')
    if 'homework_name' not in homework:
        raise KeyError('Не найдено имя проекта')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise KeyError('Не найден статус последнего проекта')
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Функция для отправки сообщения."""
    logging.info('Отправка сообщения о статусе домашней работы.')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение отправлено.')
    except Exception as error:
        logging.error(error)


def main():
    """Основная логика работы бота."""
    logging.info('Запуск бота.')

    if check_tokens():
        logging.info('Переменные окружения найдены.')
    else:
        logging.critical('Переменные окружения не найдены!')
        raise TokenError('Переменные окружения не найдены!')

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if len(response['homeworks']) == 0:
                logging.debug('Домашняя работа не найдена.')
                raise ResponseError
            homework = response['homeworks'][0]
            message = parse_status(homework)
            send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
