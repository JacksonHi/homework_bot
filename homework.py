import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiRequestError

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 6
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

last_response = ''


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('сообщение отправлено')
    except Exception:
        logger.error(f'сбой отправки сообщения {Exception}')


def send_message2(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        global last_response
        if message != last_response:
            bot.send_message(TELEGRAM_CHAT_ID, message)
            last_response = message
            logger.info('сообщение отправлено')
            return last_response
        else:
            logger.info('сообщение повторяется')
    except Exception:
        logger.error(f'сбой отправки сообщения {Exception}')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = HEADERS
    try:
        response = requests.get(ENDPOINT, params=params, headers=headers)
        if response.status_code != HTTPStatus.OK:
            logger.error(f'эндпоинт недоступен: {ENDPOINT}')
            raise Exception(f'ошибка {response}')
        return response.json()
    except Exception:
        raise ApiRequestError('API не отвечает')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if len(response['homeworks']) == 0:
        raise IndexError('homeworks пуст')
    if not isinstance(response, dict):
        raise TypeError('ожидается словарь')
    if type(response['homeworks']) != list:
        raise TypeError('ожидался список')
    return response


def parse_status(homework):
    """Извлекает статус из конкретной домашней работы."""
    keys = ['status', 'homework_name']
    for key in keys:
        if key not in homework:
            message = f'ключ {key} отсутствует'
            raise KeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'неизвестный статус'
        raise KeyError(message)
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if token is None:
            logger.critical(f'отсутствует токен {token}')
            return False
    return True


def message_replay_check(message, last_response):
    """Не пропускает повторяющиеся сообщения."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    if message != last_response:
        last_response = message
        logger.info('сообщение не повторяется')
        send_message(bot, message)
    else:
        logger.info('сообщение повторяется')
    return last_response
    # не нравится что каждый раз перезаписывается переменная, но работает.
    # если читаешь, значит еще не нащел выход :)


def main():
    """Основная логика работы бота."""
    current_timestamp = int(time.time())
    last_response = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            if check_response(response):
                message = parse_status(response['homeworks'][0])
                last_response = message_replay_check(message, last_response)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            last_response = message_replay_check(message, last_response)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    if check_tokens():
        main()
