import os

from collections import defaultdict
from openai import OpenAI
from telebot import TeleBot

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FONT_EVOLVENTA = os.path.join(BASE_DIR, 'assets/fonts/Evolventa-Regular.ttf')
FONT_EVOLVENTA_BOLD = os.path.join(BASE_DIR, 'assets/fonts/Evolventa-Bold.ttf')
FONT_PACIFICO = os.path.join(BASE_DIR, 'assets/fonts/Pacifico-Regular.ttf')
FONT_NOTO = os.path.join(BASE_DIR, 'assets/fonts/NotoEmoji-VariableFont_wght.ttf')
FONT_ARIAL = os.path.join(BASE_DIR, 'assets/fonts/ARIAL.TTF')
FONT_ARIAL_BOLD = os.path.join(BASE_DIR, 'assets/fonts/ARIALBD.TTF')
FONT_MANROPE = os.path.join(BASE_DIR, 'assets/fonts/Manrope-Regular.ttf')
FONT_MANROPE_BOLD = os.path.join(BASE_DIR, 'assets/fonts/Manrope-Bold.ttf')
FONT_ROBOTO = os.path.join(BASE_DIR, 'assets/fonts/Roboto-Regular.ttf')
FONT_ROBOTO_BOLD = os.path.join(BASE_DIR, 'assets/fonts/Roboto-Bold.ttf')

COMMENDATION_TEMPLATE_NETRONIC = os.path.join(BASE_DIR, 'assets/images/commendation_template_netronic.png')
COMMENDATION_TEMPLATE_SKIFTECH = os.path.join(BASE_DIR, 'assets/images/commendation_template_skiftech.png')
COMMENDATION_TEMPLATE_OLD = os.path.join(BASE_DIR, 'assets/images/commendation_template.png')

SESSION_ENCRYPTED_PATH = os.path.join(BASE_DIR, 'sessions/userbot_session_encrypted')
SESSION_DECRYPTED_PATH = os.path.join(BASE_DIR, 'sessions/userbot_session.session')

BIRTHDAY_NOTIFICATIONS_USER_IDS = os.getenv('BIRTHDAY_NOTIFICATION_USER_IDS')

DATABASE_URL = os.environ.get('DATABASE_URL')

BOT_TOKEN = os.environ.get('NETRONIC_BOT_TOKEN')

OPENAI_ASSISTANT_ID = os.environ.get('OPENAI_ASSISTANT_ID')

FERNET_KEY = os.environ.get('FERNET_KEY')

COMMENDATIONS_PER_PAGE = 10

TZ = os.environ.get('TZ', 'Europe/Kiev')

MONTH_DICT = {
    1: 'Січень 🌨️',
    2: 'Лютий ❄️',
    3: 'Березень 🌸',
    4: 'Квітень 🌷',
    5: 'Травень 🌼',
    6: 'Червень 🌞',
    7: 'Липень 🌴',
    8: 'Серпень 🏖️',
    9: 'Вересень 🍂',
    10: 'Жовтень 🎃',
    11: 'Листопад 🍁',
    12: 'Грудень 🎄'
}

DEPARTMENTS_DICT = {
    'D7': ['Лавренов Юрій Васильович', 'Очеретна Ганна', 'Мельникова Анастасія', 'Трофімов Павло',
           'Стеценко Олександра', 'Вдовенко Артем'],
    'D1': ['Будзан Софія'],
    'D2': ['Кучерук Дмитро'],
    'D3': ['Ігнатоля Олена'],
    'D4': ['Акулова Ірина', 'Шаповал Ростислав', 'Ушкац Ігор'],
    'D5': ['Коростильова Яна'],
    'D6': ['Степанчук Ганна'],
}

authorized_ids = {
    'users': set(),
    'admins': set(),
    'moderators': set(),
    'temp_users': set(),
}

user_data = {
    'edit_link_mode': {},
    'messages_to_delete': {},
    'form_messages_to_delete': {},
    'forms_ans': {},
    'forms_timer': {},
}

edit_link_data = {
    'saved_message': {},
    'column': {},
    'show_back_btn': {},
}

edit_employee_data = defaultdict(dict)

add_keyword_data = defaultdict(dict)

add_director_data = defaultdict(dict)

add_link_data = defaultdict(dict)

add_employee_data = defaultdict(dict)

openai_data = defaultdict(dict)

make_card_data = defaultdict(dict)

add_sub_department_data = defaultdict(dict)

secret_santa_data = defaultdict(dict)

netronic_pulse_data = defaultdict(dict)

process_in_progress = {}

client = OpenAI()
bot = TeleBot(BOT_TOKEN)
