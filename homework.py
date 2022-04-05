import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')
HEADERS = {'Authorization': f'OAuth { PRACTICUM_TOKEN }'}
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        return bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as sending_error:
        logging.error(f'Ошибка отправки Telegram: {sending_error}')


def get_api_answer(current_timestamp):
    """Получение ответа от API Практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            raise HTTPStatus.Internal_server_error(
                f'Ошибка {homework_statuses}'
            )
        return homework_statuses.json()
    except (requests.exceptions.RequestException, ValueError) as error:
        logging.error(f'Ошибка {error}')


def check_response(response):
    """Проверка ответа от API Практикума."""
    if not response:
        raise TypeError('Ничего нет')
    if not isinstance(response, dict):
        raise TypeError('Нужен словарь')
    homework = response.get('homeworks')
    if not isinstance(homework, list) or homework is None:
        raise TypeError('Нужен список')
    return homework


def parse_status(homework):
    """Извлечения названия и статуса д/з из ответа API."""
    try:
        homework_name = homework['homework_name']
        verdict = HOMEWORK_STATUSES[homework['status']]
    except Exception as error:
        raise KeyError(f'Ошибка {error}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов от Telegram и Практикума."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if token is None:
            logging.critical('Токен отсутствует!')
            return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if check_response(response):
                send_message(
                    bot, parse_status(response.get('homeworks')[0])
                )
            current_timestamp = response.get(
                'current_date', current_timestamp
            )
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)
        else:
            continue


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s',
        handlers=[logging.StreamHandler(stream=sys.stdout),
                  logging.FileHandler(filename=__file__ + '.log')]
    )
    main()
