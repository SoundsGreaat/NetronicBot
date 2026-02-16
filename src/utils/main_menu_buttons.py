import copy
from telebot import types


def create_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    knowledge_base_button = types.KeyboardButton('🎓 Навчання')
    business_processes_button = types.KeyboardButton('💼 Бізнес-процеси')
    news_feed_button = types.KeyboardButton('🔗 Стрічка новин')
    contacts_button = types.KeyboardButton('📞 Контакти')
    make_card_button = types.KeyboardButton('📜 Меню подяк')
    birthday_button = types.KeyboardButton('🎂 Дні народження')
    # secret_santa_button = types.KeyboardButton('🎅 Таємний Санта')
    netronic_pulse_button = types.KeyboardButton('💙 Питання на NETRONIC Pulse')
    support_button = types.KeyboardButton('💭 Зауваження по роботі боту')

    markup.row(knowledge_base_button, business_processes_button)
    markup.row(news_feed_button, contacts_button)
    markup.row(make_card_button, birthday_button)
    markup.row(netronic_pulse_button, support_button)

    admin_markup = copy.deepcopy(markup)

    awards_button = types.KeyboardButton('🏆 Нагороди')
    referral_button = types.KeyboardButton('🤝 Реферальна програма')
    admin_markup.row(awards_button, referral_button)
    # admin_markup.row(secret_santa_button)

    # secret_santa_markup = copy.deepcopy(markup)

    # secret_santa_markup.row(secret_santa_button)

    # secret_santa_markup = copy.deepcopy(markup)

    # secret_santa_markup.row(secret_santa_button)

    return markup, admin_markup


main_menu, admin_menu = create_main_menu()
button_names = [btn['text'] for row in admin_menu.keyboard for btn in row]
old_button_names = ['🎓 База знань', '🎅 Таємний Санта', '📊 Питання на NETRONIC Pulse']
