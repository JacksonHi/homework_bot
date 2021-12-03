import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """
        отправляет сообщение в Telegram чат, определяемый переменной
        окружения TELEGRAM_CHAT_ID. Принимает на вход два параметра:
        экземпляр класса Bot и строку с текстом сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'сообщение отправлено')
    except Exception:
        logging.error(f'сбой отправки сообщения {Exception}')


def get_api_answer(current_timestamp):
    """
        делает запрос к единственному эндпоинту API-сервиса. В качестве
        параметра функция получает временную метку. В случае успешного
        запроса должна вернуть ответ API, преобразовав его из формата
        JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers={'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    response = requests.get(ENDPOINT,params=params, headers=headers)
    if response.status_code != HTTPStatus.OK:
        logging.error(f'эндпоинт недоступен: {ENDPOINT}')
        raise Exception(f'ошибка {response}')
    return response.json()


def check_response(response):
    """
        проверяет ответ API на корректность. В качестве параметра функция
        получает ответ API, приведенный к типам данных Python. Если ответ
        API соответствует ожиданиям, то функция должна вернуть список
        домашних работ (он может быть и пустым), доступный в ответе API
        по ключу 'homeworks'.
    """
    if not response:
        raise TypeError('пустой')
    if type(response) != dict:
        raise TypeError('ожидается словарь')
    if type(response['homeworks']) != list:
        raise TypeError('ожидался список')
    return response


def parse_status(homework):
    """
        извлекает из информации о конкретной домашней работе статус этой
        работы. В качестве параметра функция получает только один элемент
        из списка домашних работ. В случае успеха, функция возвращает
        подготовленную для отправки в Telegram строку, содержащую один из
        вердиктов словаря HOMEWORK_STATUSES.
    """
    keys = ['status', 'homework_name']
    for key in keys:
        if key not in homework:
            message = f'ключ {key} отсутствует'
            raise KeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        message = 'неизвестный статус'
        raise KeyError(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """
        проверяет доступность переменных окружения, которые необходимы для
        работы программы. Если отсутствует хотя бы одна переменная
        окружения — функция должна вернуть False, иначе — True.
    """
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if token != None:
            return True
        logging.critical(f'отсутствует токен {token}')
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            current_timestamp = get_api_answer(current_timestamp)
            if check_response(current_timestamp):
                message = parse_status(current_timestamp['homeworks'][0])
                send_message(bot, message)
            time.sleep(RETRY_TIME)

        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    if check_tokens():
        main()
