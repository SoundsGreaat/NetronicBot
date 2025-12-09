import asyncio
import datetime
import math

from telebot import types, apihelper

from config import bot, COMMENDATIONS_PER_PAGE, process_in_progress, make_card_data, authorized_ids
from database import DatabaseConnection, find_contact_by_name
from handlers import authorized_only, thanks_menu
from integrations.telethon_functions import send_photo
from utils.logger import logger
from utils.make_card import make_card, make_card_old
from utils.main_menu_buttons import button_names
from utils.scheduler import scheduler, run_update_commendations_in_sheet, \
    run_create_monthly_commendation_details_sheet, run_update_all_commendations_in_sheet


@bot.callback_query_handler(func=lambda call: call.data == 'show_thanks')
@authorized_only(user_type='moderators')
def show_thanks(call):
    week_thanks_button = types.InlineKeyboardButton(text='📅 За тиждень', callback_data='time_thanks_week')
    month_thanks_button = types.InlineKeyboardButton(text='📅 За місяць', callback_data='time_thanks_month')
    year_thanks_button = types.InlineKeyboardButton(text='📅 За рік', callback_data='time_thanks_year')
    all_thanks_button = types.InlineKeyboardButton(text='📅 Всі', callback_data='time_thanks_all')
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(week_thanks_button, month_thanks_button, year_thanks_button, all_thanks_button)
    bot.edit_message_text('🔍 Оберіть період:', call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'show_my_thanks')
@authorized_only(user_type='users')
def show_my_thanks(call):
    with DatabaseConnection() as (conn, cursor):
        cursor.execute('SELECT id FROM employees WHERE telegram_user_id = %s', (call.from_user.id,))
        employee_id = cursor.fetchone()[0]
        cursor.execute('SELECT name, position FROM employees WHERE id = %s', (employee_id,))
        employee_name, employee_position = cursor.fetchone()
        cursor.execute('SELECT id, commendation_text, commendation_date FROM commendations WHERE employee_to_id = %s '
                       'ORDER BY commendation_date DESC', (employee_id,))
        commendations = cursor.fetchall()

    if not commendations:
        bot.edit_message_text('🔍 У вас немає подяк.', call.message.chat.id, call.message.message_id)
        return

    back_btn = types.InlineKeyboardButton(text='🔙 Назад', callback_data='comm_menu')
    markup = types.InlineKeyboardMarkup()
    for commendation_id, commendation_text, commendation_date in commendations:
        formatted_date = commendation_date.strftime('%d.%m.%Y')
        message_text = f'👨‍💻 {employee_name} | {formatted_date}\n\n{commendation_text}'
        markup.add(types.InlineKeyboardButton(text=message_text, callback_data=f'commendation_{commendation_id}'))

    markup.add(back_btn)
    bot.edit_message_text(f'📜 Ваші подяки:', call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'comm_menu')
@authorized_only(user_type='users')
def comm_menu(call):
    thanks_menu(call.message, edit_message=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('time_thanks_'))
@authorized_only(user_type='moderators')
def show_thanks_period(call):
    data = call.data.split('_')
    period = data[2]
    page = int(data[3]) if len(data) > 3 else 1
    today = datetime.date.today()

    if period == 'week':
        start_date = today - datetime.timedelta(days=7)
    elif period == 'month':
        start_date = today.replace(day=1)
    elif period == 'year':
        start_date = today.replace(day=1, month=1)
    else:
        start_date = None

    with DatabaseConnection() as (conn, cursor):
        if start_date:
            cursor.execute(
                'SELECT commendations.id, name, commendations.position, commendation_text, commendation_date '
                'FROM commendations '
                'JOIN employees ON employee_to_id = employees.id '
                'WHERE commendation_date >= %s '
                'ORDER BY commendation_date DESC', (start_date,)
            )
        else:
            cursor.execute(
                'SELECT commendations.id, name, commendations.position, commendation_text, commendation_date '
                'FROM commendations '
                'JOIN employees ON employee_to_id = employees.id '
                'ORDER BY commendation_date DESC'
            )
        commendations = cursor.fetchall()

    back_btn = types.InlineKeyboardButton(text='🔙 Назад', callback_data='show_thanks')
    markup = types.InlineKeyboardMarkup()

    if not commendations:
        markup.add(back_btn)
        bot.edit_message_text('🔍 Подяк немає.', call.message.chat.id, call.message.message_id,
                              reply_markup=markup)
        return

    total_pages = math.ceil(len(commendations) / COMMENDATIONS_PER_PAGE)
    start_index = (page - 1) * COMMENDATIONS_PER_PAGE
    end_index = start_index + COMMENDATIONS_PER_PAGE
    commendations_page = commendations[start_index:end_index]

    for commendation in commendations_page:
        commendation_id, employee_name, employee_position, _, commendation_date = commendation
        formatted_date = commendation_date.strftime('%d.%m.%Y')
        split_name = employee_name.split()
        formatted_name = f'{split_name[0]} {split_name[1][0]}'
        button_text = f'👨‍💻 {formatted_name} | {formatted_date}'
        markup.add(types.InlineKeyboardButton(text=button_text, callback_data=f'commendation_{commendation_id}'))

    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            types.InlineKeyboardButton(text='⬅️', callback_data=f'time_thanks_{period}_{page - 1}'))
    if page < total_pages:
        nav_buttons.append(
            types.InlineKeyboardButton(text='➡️', callback_data=f'time_thanks_{period}_{page + 1}'))
    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(back_btn)
    bot.edit_message_text(f'📜 Подяки ({page}/{total_pages}):', call.message.chat.id, call.message.message_id,
                          reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('commendation_'))
@authorized_only(user_type='users')
def show_commendation(call):
    commendation_id = int(call.data.split('_')[1])
    with DatabaseConnection() as (conn, cursor):
        cursor.execute(
            '''
            SELECT e_to.name,
                   commendations.position,
                   commendation_text,
                   commendation_date,
                   e_from.name,
                   values.name,
                   e_from.position,
                   com_sender.sender_name
            FROM commendations
                     JOIN employees e_to ON employee_to_id = e_to.id
                     JOIN employees e_from ON employee_from_id = e_from.id
                     LEFT JOIN commendation_values values ON commendations.value_id = values.id
                     LEFT JOIN commendation_senders com_sender ON commendations.id = com_sender.commendation_id
            WHERE commendations.id = %s
            ''',
            (commendation_id,)
        )
        employee_name, employee_position, commendation_text, commendation_date, employee_from_name, \
            value_name, employee_from_position, sender_name = cursor.fetchone()

    formatted_date = commendation_date.strftime('%d.%m.%Y')

    # TODO change template
    if not value_name:
        image = make_card_old(employee_name, employee_position, commendation_text)
    else:
        if sender_name:
            employee_from_name = sender_name
            employee_from_position = None

        image = make_card(employee_name, employee_position, commendation_text, value_name, employee_from_name,
                          employee_from_position)

    message_text = (f'👨‍💻 <b>{employee_name}</b> | {formatted_date}\n\nВід <b>{employee_from_name}</b>'
                    f'\nЦінність: <b>{value_name if value_name else "Не вказано"}</b>'
                    f'\n\n{commendation_text}')
    delete_btn = types.InlineKeyboardButton(text='🗑️ Видалити', callback_data=f'delcommendation_{commendation_id}')
    hide_btn = types.InlineKeyboardButton(text='❌ Сховати', callback_data='hide_message')
    markup = types.InlineKeyboardMarkup()
    markup.add(hide_btn)

    if call.from_user.id in authorized_ids['admins']:
        markup.add(delete_btn)

    bot.send_photo(call.message.chat.id, image, caption=message_text, reply_markup=markup, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data.startswith('delcommendation_'))
@authorized_only(user_type='admins')
def delete_commendation(call):
    commendation_id = int(call.data.split('_')[1])
    confirm_delete_btn = types.InlineKeyboardButton(text='✅ Підтвердити видалення',
                                                    callback_data=f'cdcommendation_{commendation_id}')
    back_btn = types.InlineKeyboardButton(text='❌ Скасувати видалення', callback_data='hide_message')
    markup = types.InlineKeyboardMarkup()
    markup.add(confirm_delete_btn, back_btn)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cdcommendation_'))
@authorized_only(user_type='admins')
def confirm_delete_commendation(call):
    commendation_id = int(call.data.split('_')[1])
    with DatabaseConnection() as (conn, cursor):
        cursor.execute('DELETE FROM commendations WHERE id = %s', (commendation_id,))
        conn.commit()

    scheduler.add_job(run_update_commendations_in_sheet, trigger='date', run_date=datetime.datetime.now())

    bot.delete_message(call.message.chat.id, call.message.message_id)
    logger.info(f'Commendation {commendation_id} deleted by {call.from_user.username}.')
    bot.send_message(call.message.chat.id, '✅ Подяку видалено.')


@bot.callback_query_handler(func=lambda call: call.data == 'send_commendation_mod')
@authorized_only(user_type='users')
def choose_branch(call):
    if make_card_data.get(call.message.chat.id):
        del make_card_data[call.message.chat.id]

    markup = types.InlineKeyboardMarkup(row_width=1)
    netronic_btn = types.InlineKeyboardButton(text='📘 Надіслати подяку NETRONIC',
                                              callback_data='send_commendation_mod_netronic')
    skiftech_btn = types.InlineKeyboardButton(text='🏮 Надіслати подяку SKIFTECH',
                                              callback_data='send_commendation_mod_skiftech')
    markup.add(netronic_btn, skiftech_btn)

    bot.edit_message_text('🔍 Оберіть гілку:', call.message.chat.id,
                                         call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('send_commendation_mod_'))
@authorized_only(user_type='users')
def choose_sender(call):
    branch = call.data.split('_')[-1]
    markup = types.InlineKeyboardMarkup(row_width=1)
    send_from_me_btn = types.InlineKeyboardButton(text='📩 Від мого імені', callback_data='thanks_from_me_mod')
    send_from_other_btn = types.InlineKeyboardButton(text='📩 Від департаменту/іншого співробітника',
                                                     callback_data='thanks_from_other_mod')
    markup.add(send_from_me_btn, send_from_other_btn)

    sent_message = bot.edit_message_text('🔍 Оберіть варіант надсилання подяки:', call.message.chat.id,
                                         call.message.message_id, reply_markup=markup)

    make_card_data[call.message.chat.id]['branch'] = branch
    make_card_data[call.message.chat.id]['sent_message'] = sent_message


@bot.callback_query_handler(func=lambda call: call.data == 'thanks_from_me_mod')
@authorized_only(user_type='users')
def thanks_search(call):
    process_in_progress[call.message.chat.id] = 'thanks_search_mod'

    cancel_btn = types.InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_send_thanks')
    markup = types.InlineKeyboardMarkup()
    markup.add(cancel_btn)
    sent_message = bot.edit_message_text('📝 Введіть ім\'я співробітника якому хочете надіслати подяку:',
                                         call.message.chat.id, call.message.message_id, reply_markup=markup)
    make_card_data[call.message.chat.id]['sent_message'] = sent_message


@bot.callback_query_handler(func=lambda call: call.data == 'thanks_from_other_mod')
@authorized_only(user_type='users')
def thanks_send_sender(call):
    process_in_progress[call.message.chat.id] = 'thanks_send_sender_mod'

    cancel_btn = types.InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_send_thanks')
    markup = types.InlineKeyboardMarkup()
    markup.add(cancel_btn)
    sent_message = bot.edit_message_text('📝 Введіть ім\'я співробітника, від імені якого хочете надіслати подяку:',
                                         call.message.chat.id, call.message.message_id, reply_markup=markup)
    make_card_data[call.message.chat.id]['sent_message'] = sent_message


@bot.message_handler(func=lambda message: message.text not in button_names and process_in_progress.get(
    message.chat.id) == 'thanks_send_sender_mod')
@authorized_only(user_type='users')
def thanks_send_sender_ans(message):
    process_in_progress[message.chat.id] = 'thanks_search_mod'

    sender_name = message.text
    make_card_data[message.chat.id]['sender_name'] = sender_name
    bot.delete_message(message.chat.id, message.message_id)
    sent_message = make_card_data[message.chat.id]['sent_message']

    cancel_btn = types.InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_send_thanks')
    markup = types.InlineKeyboardMarkup()
    markup.add(cancel_btn)

    bot.edit_message_text(f'✅ Ім\'я відправника встановлено як: {sender_name}\n'
                          f'📝 Введіть ім\'я співробітника якому хочете надіслати подяку:',
                          message.chat.id, sent_message.message_id, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text not in button_names and process_in_progress.get(
    message.chat.id) == 'thanks_search_mod')
@authorized_only(user_type='users')
def proceed_thanks_search(message):
    search_query = message.text
    found_contacts = find_contact_by_name(search_query)
    sent_message = make_card_data[message.chat.id]['sent_message']
    if found_contacts:
        markup = types.InlineKeyboardMarkup(row_width=1)

        for employee_info in found_contacts:
            employee_id = employee_info[0]
            employee_name = employee_info[1]
            employee_position = employee_info[2]

            formatted_name = employee_name.split()
            formatted_name = f'{formatted_name[0]} {formatted_name[1]}'
            btn = types.InlineKeyboardButton(text=f'👨‍💻 {formatted_name} - {employee_position}',
                                             callback_data=f'thanksmod_{employee_id}')
            markup.add(btn)
        cancel_btn = types.InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_send_thanks')
        markup.add(cancel_btn)
        bot.delete_message(message.chat.id, message.message_id)
        sent_message = bot.edit_message_text('🔍 Оберіть співробітника:', message.chat.id, sent_message.message_id,
                                             reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('thanksmod_'))
@authorized_only(user_type='users')
def proceed_send_thanks(call):
    employee_id = int(call.data.split('_')[1])
    process_in_progress[call.message.chat.id] = 'send_thanks_mod'
    with DatabaseConnection() as (conn, cursor):
        cursor.execute('SELECT name, position, telegram_user_id FROM employees WHERE id = %s', (employee_id,))
        employee_data = cursor.fetchone()
    employee_name = employee_data[0]
    employee_position = employee_data[1]
    employee_telegram_id = employee_data[2]

    employee_name_basic = employee_name
    make_card_data[call.message.chat.id]['employee_id'] = employee_id
    make_card_data[call.message.chat.id]['employee_name_basic'] = employee_name_basic
    make_card_data[call.message.chat.id]['employee_position'] = employee_position
    make_card_data[call.message.chat.id]['employee_telegram_id'] = employee_telegram_id
    markup = types.InlineKeyboardMarkup(row_width=1)

    with DatabaseConnection() as (conn, cursor):
        cursor.execute('SELECT id, name FROM commendation_values')
        values = cursor.fetchall()

    for value in values:
        value_id = value[0]
        value_name = value[1]
        btn = types.InlineKeyboardButton(text=f'{value_name}', callback_data=f'valuemod_{value_id}')
        markup.add(btn)
    sent_message = bot.edit_message_text(
        f'Виберіть цінність, якій відповідає подяка:',
        call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)
    make_card_data[call.message.chat.id]['sent_message'] = sent_message


@bot.callback_query_handler(func=lambda call: call.data.startswith('valuemod_'))
@authorized_only(user_type='users')
def select_value(call):
    value_id = int(call.data.split('_')[1])
    make_card_data[call.message.chat.id]['value'] = value_id
    employee_name_basic = make_card_data[call.message.chat.id]['employee_name_basic']

    sent_message = bot.edit_message_text(
        '📝 Введіть текст подяки (не більше 150 символів):',
        call.message.chat.id, call.message.message_id, parse_mode='HTML')

    make_card_data[call.message.chat.id]['sent_message'] = sent_message


@bot.message_handler(func=lambda message: message.text not in button_names and process_in_progress.get(
    message.chat.id) == 'send_thanks_mod')
@authorized_only(user_type='users')
def send_thanks_name_mod(message, position_changed=False):
    if len(message.text) >= 150:
        bot.reply_to(message, '❗️ Текст подяки не може перевищувати 150 символів.')
        return

    data_filled = False

    if not make_card_data[message.chat.id].get('thanks_text'):
        make_card_data[message.chat.id]['thanks_text'] = message.text
        sent_message = make_card_data[message.chat.id]['sent_message']
        bot.delete_message(message.chat.id, message.message_id)
        bot.delete_message(message.chat.id, sent_message.message_id)
        data_filled = True

    if data_filled or position_changed:
        with DatabaseConnection() as (conn, cursor):
            cursor.execute('SELECT name, position FROM employees WHERE telegram_user_id = %s',
                           (message.chat.id,))
            employee_from_name, employee_from_position = cursor.fetchone()

            cursor.execute('SELECT name FROM commendation_values WHERE id = %s',
                           (make_card_data[message.chat.id]['value'],))
            value_name = cursor.fetchone()[0]

        if make_card_data[message.chat.id].get('sender_name'):
            employee_from_name = make_card_data[message.chat.id]['sender_name']
            employee_from_position = None

        image = make_card(
            make_card_data[message.chat.id]['employee_name_basic'],
            make_card_data[message.chat.id]['employee_position'],
            make_card_data[message.chat.id]['thanks_text'],
            value_name,
            employee_from_name,
            employee_from_position
        )

        make_card_data[message.chat.id]['image'] = image

        markup = types.InlineKeyboardMarkup(row_width=2)
        confirm_btn = types.InlineKeyboardButton(text='✅ Підтвердити', callback_data='confirm_send_thanks_mod')
        position_change_btn = types.InlineKeyboardButton(text='🔄 Змінити посаду',
                                                         callback_data='com_change_position_mod')
        cancel_btn = types.InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_send_thanks')
        markup.add(confirm_btn, cancel_btn, position_change_btn)

        sent_message = bot.send_photo(message.chat.id, image, caption='📝 Перевірте подяку:', reply_markup=markup)
        make_card_data[message.chat.id]['sent_message'] = sent_message


@bot.callback_query_handler(func=lambda call: call.data == 'confirm_send_thanks_mod')
@authorized_only(user_type='users')
def confirm_send_thanks(call):
    sent_message = make_card_data[call.message.chat.id]['sent_message']
    bot.delete_message(call.message.chat.id, sent_message.message_id)
    recipient_id = make_card_data[call.message.chat.id]['employee_telegram_id']
    image = make_card_data[call.message.chat.id]['image']

    employee_id = make_card_data[call.message.chat.id]['employee_id']
    commendation_text = make_card_data[call.message.chat.id]['thanks_text']
    employee_position = make_card_data[call.message.chat.id]['employee_position']
    value_id = make_card_data[call.message.chat.id]['value']
    branch = make_card_data[call.message.chat.id]['branch']
    commendation_date = datetime.datetime.now().date()

    with DatabaseConnection() as (conn, cursor):
        cursor.execute('SELECT id FROM employees WHERE telegram_user_id = %s', (call.message.chat.id,))
        sender_id = cursor.fetchone()[0]
        cursor.execute(
            'INSERT INTO commendations_mod ('
            'employee_to_id, employee_from_id, commendation_text, commendation_date, position, '
            'value_id, branch) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id',
            (employee_id, sender_id, commendation_text, commendation_date, employee_position, value_id, branch)
        )
        commendation_id = cursor.fetchone()[0]
        conn.commit()

        if make_card_data[call.message.chat.id].get('sender_name'):
            sender_name = make_card_data[call.message.chat.id]['sender_name']

            cursor.execute(
                'INSERT INTO commendation_senders_mod ('
                'commendation_id, sender_name) '
                'VALUES (%s, %s)',
                (commendation_id, sender_name)
            )
            conn.commit()

    scheduler.add_job(run_update_all_commendations_in_sheet, trigger='date', run_date=datetime.datetime.now())

    bot.send_photo(call.message.chat.id, image, caption='✅ Подяку надіслано на модерацію.'
                                                        '\nДякуємо за вашу залученість!')

    del make_card_data[call.message.chat.id]
    if process_in_progress.get(call.message.chat.id):
        del process_in_progress[call.message.chat.id]


@bot.callback_query_handler(func=lambda call: call.data == 'com_change_position_mod')
@authorized_only(user_type='users')
def com_change_position(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    process_in_progress[call.message.chat.id] = 'com_change_position_mod'
    sent_message = bot.send_message(call.message.chat.id, '💼 Введіть нову посаду:')
    make_card_data[call.message.chat.id]['sent_message'] = sent_message


@bot.message_handler(func=lambda message: message.text not in button_names and process_in_progress.get(
    message.chat.id) == 'com_change_position_mod')
@authorized_only(user_type='users')
def com_change_position_ans(message):
    make_card_data[message.chat.id]['employee_position'] = message.text
    sent_message = make_card_data[message.chat.id]['sent_message']
    bot.delete_message(message.chat.id, message.message_id)
    bot.delete_message(message.chat.id, sent_message.message_id)

    del process_in_progress[message.chat.id]

    send_thanks_name_mod(message, position_changed=True)


@bot.callback_query_handler(func=lambda call: call.data == 'send_thanks')
@authorized_only(user_type='moderators')
def send_thanks(call):
    process_in_progress[call.message.chat.id] = 'thanks_search'

    if make_card_data.get(call.message.chat.id):
        del make_card_data[call.message.chat.id]

    cancel_btn = types.InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_send_thanks')
    markup = types.InlineKeyboardMarkup()
    markup.add(cancel_btn)
    sent_message = bot.edit_message_text('📝 Введіть ім\'я співробітника для пошуку:',
                                         call.message.chat.id, call.message.message_id, reply_markup=markup)
    make_card_data[call.message.chat.id]['sent_message'] = sent_message


@bot.message_handler(func=lambda message: message.text not in button_names and process_in_progress.get(
    message.chat.id) == 'thanks_search')
@authorized_only(user_type='moderators')
def proceed_thanks_search(message):
    search_query = message.text
    found_contacts = find_contact_by_name(search_query)
    sent_message = make_card_data[message.chat.id]['sent_message']
    if found_contacts:
        markup = types.InlineKeyboardMarkup(row_width=1)

        for employee_info in found_contacts:
            employee_id = employee_info[0]
            employee_name = employee_info[1]
            employee_position = employee_info[2]

            formatted_name = employee_name.split()
            formatted_name = f'{formatted_name[0]} {formatted_name[1]}'
            btn = types.InlineKeyboardButton(text=f'👨‍💻 {formatted_name} - {employee_position}',
                                             callback_data=f'thanks_{employee_id}')
            markup.add(btn)
        cancel_btn = types.InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_send_thanks')
        markup.add(cancel_btn)
        bot.delete_message(message.chat.id, message.message_id)
        sent_message = bot.edit_message_text('🔍 Оберіть співробітника:', message.chat.id, sent_message.message_id,
                                             reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('thanks_'))
@authorized_only(user_type='moderators')
def proceed_send_thanks(call):
    employee_id = int(call.data.split('_')[1])
    process_in_progress[call.message.chat.id] = 'send_thanks'
    with DatabaseConnection() as (conn, cursor):
        cursor.execute('SELECT name, position, telegram_user_id FROM employees WHERE id = %s', (employee_id,))
        employee_data = cursor.fetchone()
    employee_name = employee_data[0]
    employee_position = employee_data[1]
    employee_telegram_id = employee_data[2]

    employee_name_basic = employee_name
    make_card_data[call.message.chat.id]['employee_id'] = employee_id
    make_card_data[call.message.chat.id]['employee_name_basic'] = employee_name_basic
    make_card_data[call.message.chat.id]['employee_position'] = employee_position
    make_card_data[call.message.chat.id]['employee_telegram_id'] = employee_telegram_id

    sent_message = bot.edit_message_text(
        '📝 Введіть текст подяки (не більше 150 символів):',
        call.message.chat.id, call.message.message_id, parse_mode='HTML')
    make_card_data[call.message.chat.id]['sent_message'] = sent_message


@bot.message_handler(func=lambda message: message.text not in button_names and process_in_progress.get(
    message.chat.id) == 'send_thanks')
@authorized_only(user_type='moderators')
def send_thanks_name(message, position_changed=False):
    if len(message.text) >= 150:
        bot.reply_to(message, '❗️ Текст подяки не може перевищувати 150 символів.')
        return

    data_filled = False

    if not make_card_data[message.chat.id].get('thanks_text'):
        make_card_data[message.chat.id]['thanks_text'] = message.text
        sent_message = make_card_data[message.chat.id]['sent_message']
        bot.delete_message(message.chat.id, message.message_id)
        bot.delete_message(message.chat.id, sent_message.message_id)
        data_filled = True

    if data_filled or position_changed:
        if data_filled or position_changed:
            with DatabaseConnection() as (conn, cursor):
                cursor.execute('SELECT name, position FROM employees WHERE telegram_user_id = %s',
                               (message.chat.id,))
                employee_from_name, employee_from_position = cursor.fetchone()

                # cursor.execute('SELECT name FROM commendation_values WHERE id = %s',
                #                (make_card_data[message.chat.id]['value'],))
                # value_name = cursor.fetchone()[0]

        image = make_card_old(
            make_card_data[message.chat.id]['employee_name_basic'],
            make_card_data[message.chat.id]['employee_position'],
            make_card_data[message.chat.id]['thanks_text'],
            # TODO change template
            # value_name,
            # employee_from_name,
            # employee_from_position
        )
        make_card_data[message.chat.id]['image'] = image

        markup = types.InlineKeyboardMarkup(row_width=2)
        confirm_btn = types.InlineKeyboardButton(text='✅ Підтвердити', callback_data='confirm_send_thanks')
        position_change_btn = types.InlineKeyboardButton(text='🔄 Змінити посаду', callback_data='com_change_position')
        cancel_btn = types.InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_send_thanks')
        markup.add(confirm_btn, cancel_btn, position_change_btn)

        sent_message = bot.send_photo(message.chat.id, image, caption='📝 Перевірте подяку:', reply_markup=markup)
        make_card_data[message.chat.id]['sent_message'] = sent_message


@bot.callback_query_handler(func=lambda call: call.data == 'confirm_send_thanks')
@authorized_only(user_type='moderators')
def confirm_send_thanks(call):
    sent_message = make_card_data[call.message.chat.id]['sent_message']
    bot.delete_message(call.message.chat.id, sent_message.message_id)
    recipient_id = make_card_data[call.message.chat.id]['employee_telegram_id']
    image = make_card_data[call.message.chat.id]['image']

    employee_id = make_card_data[call.message.chat.id]['employee_id']
    commendation_text = make_card_data[call.message.chat.id]['thanks_text']
    employee_position = make_card_data[call.message.chat.id]['employee_position']
    # value_id = make_card_data[call.message.chat.id]['value']
    commendation_date = datetime.datetime.now().date()

    with DatabaseConnection() as (conn, cursor):
        cursor.execute('SELECT id FROM employees WHERE telegram_user_id = %s', (call.message.chat.id,))
        sender_id = cursor.fetchone()[0]
        # TODO change template
        # cursor.execute(
        #     'INSERT INTO commendations ('
        #     'employee_to_id, employee_from_id, commendation_text, commendation_date, position, '
        #     'value_id) '
        #     'VALUES (%s, %s, %s, %s, %s, %s)',
        #     (employee_id, sender_id, commendation_text, commendation_date, employee_position, value_id)
        # )

        cursor.execute(
            'INSERT INTO commendations ('
            'employee_to_id, employee_from_id, commendation_text, commendation_date, position) '
            'VALUES (%s, %s, %s, %s, %s)',
            (employee_id, sender_id, commendation_text, commendation_date, employee_position)
        )

        conn.commit()

    scheduler.add_job(run_create_monthly_commendation_details_sheet, trigger='date', run_date=datetime.datetime.now())
    scheduler.add_job(run_update_commendations_in_sheet, trigger='date', run_date=datetime.datetime.now())

    try:
        bot.send_photo(recipient_id, image, caption='📩 Вам було надіслано подяку.')
    except apihelper.ApiTelegramException as e:
        if e.error_code == 400 and "chat not found" in e.description:
            logger.warning(f'Cannot send commendation to user {recipient_id}: chat not found.')

    bot.send_photo(call.message.chat.id, image, caption='✅ Подяку надіслано.')

    del make_card_data[call.message.chat.id]
    if process_in_progress.get(call.message.chat.id):
        del process_in_progress[call.message.chat.id]


@bot.callback_query_handler(func=lambda call: call.data == 'com_change_position')
@authorized_only(user_type='moderators')
def com_change_position(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    process_in_progress[call.message.chat.id] = 'com_change_position'
    sent_message = bot.send_message(call.message.chat.id, '💼 Введіть нову посаду:')
    make_card_data[call.message.chat.id]['sent_message'] = sent_message


@bot.message_handler(func=lambda message: message.text not in button_names and process_in_progress.get(
    message.chat.id) == 'com_change_position')
@authorized_only(user_type='moderators')
def com_change_position_ans(message):
    make_card_data[message.chat.id]['employee_position'] = message.text
    sent_message = make_card_data[message.chat.id]['sent_message']
    bot.delete_message(message.chat.id, message.message_id)
    bot.delete_message(message.chat.id, sent_message.message_id)

    del process_in_progress[message.chat.id]

    send_thanks_name(message, position_changed=True)


@bot.callback_query_handler(func=lambda call: call.data == 'cancel_send_thanks')
@authorized_only(user_type='users')
def cancel_send_thanks(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, '🚪 Створення подяки скасовано.')
    del make_card_data[call.message.chat.id]
    del process_in_progress[call.message.chat.id]


@bot.callback_query_handler(func=lambda call: call.data == 'hide_message')
@authorized_only(user_type='users')
def hide_message(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
