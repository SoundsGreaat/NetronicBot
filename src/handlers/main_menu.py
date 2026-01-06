import datetime

from telebot import types

from config import bot, MONTH_DICT, authorized_ids, make_card_data, process_in_progress
from handlers import authorized_only
from integrations.google_forms_filler import send_question_form
from utils.messages import send_links


@bot.message_handler(func=lambda message: message.text == '🎓 Навчання')
@authorized_only(user_type='users')
def send_knowledge_base(message, edit_message=False):
    send_links(message, 'knowledge_base', edit_message)


@bot.message_handler(func=lambda message: message.text == '💼 Бізнес-процеси')
@authorized_only(user_type='users')
def send_business_processes(message, edit_message=False):
    personnel_management_btn = types.InlineKeyboardButton(
        text='📁 Кадрове діловодство',
        callback_data='b_process_personnel_management'
    )

    recruitment_btn = types.InlineKeyboardButton(
        text='🕵️ Recruitment',
        callback_data='b_process_recruitment'
    )

    office_equipment_btn = types.InlineKeyboardButton(
        text='🖨️ Забезпечення офісу',
        callback_data='b_process_office_equipment'
    )

    hr_btn = types.InlineKeyboardButton(
        text='👨‍💼 HR',
        callback_data='b_process_hr'
    )

    law_department_btn = types.InlineKeyboardButton(
        text='⚖️ Заявка до юр. департаменту',
        callback_data='b_process_law'
    )

    business_initiative_btn = types.InlineKeyboardButton(
        text='💡 Бізнес-ініціатива',
        url='https://docs.google.com/forms/d/e/1FAIpQLScJlOaWdUt4wdQZVlUa2PB1c7PXEDdPShJ2bpWhrTmVRqnWQw/viewform'
    )

    helpdesk_btn = types.InlineKeyboardButton(
        text='💻 HelpDesk IT (звернення до сист. адміністраторів)',
        callback_data='b_process_helpdesk'
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        personnel_management_btn,
        recruitment_btn,
        office_equipment_btn,
        hr_btn,
        law_department_btn,
        business_initiative_btn,
        helpdesk_btn
    )
    if edit_message:
        bot.edit_message_text('🔍 Оберіть бізнес-процес для перегляду:', message.chat.id, message.message_id,
                              reply_markup=markup)
    else:
        bot.send_message(message.chat.id, '🔍 Оберіть бізнес-процес для перегляду:', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'business_processes')
@authorized_only(user_type='users')
def send_business_processes_menu(call):
    send_business_processes(call.message, edit_message=True)


@bot.message_handler(func=lambda message: message.text == '🎂 Дні народження')
@authorized_only(user_type='users')
def send_birthdays(message, edit_message=False):
    month_today = datetime.datetime.now().month
    sorted_months = list(range(month_today, 13)) + list(range(1, month_today))
    markup = types.InlineKeyboardMarkup(row_width=1)
    for month in sorted_months:
        month_btn = types.InlineKeyboardButton(text=MONTH_DICT[month], callback_data=f'birthdays_{month}')
        markup.add(month_btn)
    if edit_message:
        bot.edit_message_text('🔍 Оберіть місяць:', message.chat.id, message.message_id,
                              reply_markup=markup)
    else:
        bot.send_message(message.chat.id, '🔍 Оберіть місяць:', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == '📞 Контакти')
@authorized_only(user_type='users')
def send_contacts_menu(message, edit_message=False):
    search_btn = types.InlineKeyboardButton(text='🔎 Пошук співробітника', callback_data='search')
    departments_btn = types.InlineKeyboardButton(text='🏢 Департаменти', callback_data='departments')
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(search_btn, departments_btn)

    if edit_message:
        bot.edit_message_text('Оберіть дію:', message.chat.id, message.message_id, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, 'Оберіть дію:', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_send_contacts')
@authorized_only(user_type='users')
def back_to_send_contacts_menu(call):
    send_contacts_menu(call.message, edit_message=True)
    if process_in_progress.get(call.message.chat.id) == 'search':
        del process_in_progress[call.message.chat.id]


@bot.message_handler(func=lambda message: message.text == '📜 Меню подяк')
@authorized_only(user_type='users')
def thanks_menu(message, edit_message=False):
    markup = types.InlineKeyboardMarkup()
    show_my_thanks_button = types.InlineKeyboardButton(text='🔍 Мої подяки', callback_data='show_my_thanks')
    send_commendation_mod = types.InlineKeyboardButton(text='📜 Надіслати подяку',
                                                       callback_data='send_commendation_mod')
    markup.add(show_my_thanks_button)

    if message.chat.id in authorized_ids['moderators'] or message.chat.id in authorized_ids['admins']:
        show_thanks_button = types.InlineKeyboardButton(text='🔍 Передивитись подяки', callback_data='show_thanks')
        send_thanks_button = types.InlineKeyboardButton(text='📜 Розсилка старих подяк', callback_data='send_thanks')
        markup.add(show_thanks_button, send_thanks_button, row_width=1)

    markup.add(send_commendation_mod)

    if not edit_message:
        sent_message = bot.send_message(message.chat.id, '🔽 Оберіть дію:',
                                        reply_markup=markup)
        make_card_data[message.chat.id]['sent_message'] = sent_message

    else:
        sent_message = bot.edit_message_text('🔽 Оберіть дію:', message.chat.id, message.message_id,
                                             reply_markup=markup)
        make_card_data[message.chat.id]['sent_message'] = sent_message


@bot.message_handler(func=lambda message: message.text == '🏆 Нагороди')
@authorized_only(user_type='moderators')
def awards_menu(message):
    markup = types.InlineKeyboardMarkup()

    show_awards_button = types.InlineKeyboardButton(text='🔍 Передивитись нагороди', callback_data='show_awards')
    send_award_button = types.InlineKeyboardButton(text='📜 Надіслати нагороду', callback_data='send_award')
    markup.add(show_awards_button, send_award_button, row_width=1)

    sent_message = bot.send_message(message.chat.id, '🔽 Оберіть дію:',
                                    reply_markup=markup)
    make_card_data[message.chat.id]['sent_message'] = sent_message


@bot.message_handler(func=lambda message: message.text == '🤝 Реферальна програма')
@authorized_only(user_type='moderators')
def awards_menu(message):
    markup = types.InlineKeyboardMarkup()

    show_awards_button = types.InlineKeyboardButton(text='🔍 Передивитись подяки (реферальна програма)',
                                                    callback_data='show_refs')
    send_award_button = types.InlineKeyboardButton(text='📜 Надіслати подяку (реферальна програма)',
                                                   callback_data='send_ref')
    markup.add(show_awards_button, send_award_button, row_width=1)

    sent_message = bot.send_message(message.chat.id, '🔽 Оберіть дію:',
                                    reply_markup=markup)
    make_card_data[message.chat.id]['sent_message'] = sent_message


@bot.message_handler(func=lambda message: message.text == '🔗 Стрічка новин')
@authorized_only(user_type='users')
def send_useful_links(message, edit_message=False):
    send_links(message, 'news_feed', edit_message)


@bot.message_handler(func=lambda message: message.text == '💭 Зауваження по роботі боту')
@authorized_only(user_type='users')
def send_form(message):
    form_url = ('https://docs.google.com/forms/d/e/1FAIpQLSfcoy2DMzrZRtLzf8wzfDEZnk-4yIsL9uUBK5kOFBs0Q8N0dA/'
                'viewform?usp=sf_link')
    send_question_form(message, form_url)
