import os
import requests
import time
import logging
import sys

from logging import StreamHandler
from http import HTTPStatus
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import ResponseError

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


def check_tokens() -> bool:
    """Функция для проверки переменных окружения."""
    logging.info('Проверка наличия переменных окружения.')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def get_api_answer(timestamp) -> dict:
    """Функция для отправки запроса к API."""
    logging.info('Отправление запроса к API.')
    try:
        params: dict = {
            'url': ENDPOINT,
            'headers': HEADERS,
            'params': {'from_date': timestamp}
        }
        response = requests.get(**params)
        if response.status_code != HTTPStatus.OK:
            raise ResponseError('Ошибка запроса!')
        return response.json()
    except requests.RequestException:
        raise ResponseError('Ошибка запроса!')


def check_response(response) -> list:
    """Функция для проверки ответа от API."""
    logging.info('Проверка ответа API.')
    if not isinstance(response, dict):
        raise TypeError
    if 'homeworks' not in response:
        logging.debug('Домашняя работа отсутствует в ответе API!')
        raise ResponseError
    if not isinstance(response['homeworks'], list):
        raise TypeError
    return response['homeworks']


def parse_status(homework) -> str:
    """Функция для формирования сообщения."""
    logging.info('Проверка статуса домашней работы.')
    if 'homework_name' not in homework:
        raise KeyError('Не найдено имя проекта')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise KeyError('Не найден статус последнего проекта')
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message) -> None:
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

    if not check_tokens():
        logging.critical('Переменные окружения не найдены!')
        sys.exit()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                if message != previous_message:
                    send_message(bot, message)
                previous_message = message
            else:
                logging.debug('Домашняя работа не найдена.')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != previous_message:
                send_message(bot, message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
