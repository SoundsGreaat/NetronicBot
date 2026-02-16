import datetime

from config import bot, DEPARTMENTS_DICT, process_in_progress, netronic_pulse_data
from telebot import types, apihelper

from database import DatabaseConnection
from handlers import authorized_only
from utils.scheduler import scheduler, run_update_pulse_questions_in_sheet


@bot.callback_query_handler(func=lambda call: call.data.startswith('pulse_dep_'))
@authorized_only(user_type='users')
def send_netronic_pulse_employees(call):
    dept_code = call.data.split('_')[-1]
    employees = DEPARTMENTS_DICT.get(dept_code, [])

    markup = types.InlineKeyboardMarkup(row_width=1)

    back_btn = types.InlineKeyboardButton(text='🔙 Назад', callback_data='netronic_pulse_departments')

    for idx, employee_name in enumerate(employees):
        emp_btn = types.InlineKeyboardButton(text=employee_name,
                                             callback_data=f'pulse_emp_{dept_code}_{idx}')
        markup.add(emp_btn)

    markup.add(back_btn)

    try:
        bot.edit_message_text('🔍 Оберіть співробітника:', call.message.chat.id, call.message.message_id,
                              reply_markup=markup)
    except apihelper.ApiException:
        pass


@bot.callback_query_handler(func=lambda call: call.data == 'netronic_pulse_departments')
@authorized_only(user_type='users')
def back_to_departments(call):
    markup = types.InlineKeyboardMarkup(row_width=1)

    departments = DEPARTMENTS_DICT

    for dept_code, _ in departments.items():
        dept_btn = types.InlineKeyboardButton(text=dept_code, callback_data=f'pulse_dep_{dept_code}')
        markup.add(dept_btn)

    try:
        bot.edit_message_text('🔍 Оберіть департамент:', call.message.chat.id, call.message.message_id,
                              reply_markup=markup)
    except apihelper.ApiException:
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('pulse_emp_'))
@authorized_only(user_type='users')
def send_netronic_pulse_employee_pulse(call):
    _, _, dept_code, emp_idx = call.data.split('_')
    emp_idx = int(emp_idx)
    employees = DEPARTMENTS_DICT.get(dept_code, [])
    if emp_idx < 0 or emp_idx >= len(employees):
        return

    employee_name = employees[emp_idx]

    process_in_progress[call.message.chat.id] = 'netronic_pulse_question'
    netronic_pulse_data[call.message.chat.id] = {
        'employee_name': employee_name,
        'department': dept_code
    }

    sent_message = bot.edit_message_text(f'💙 Напишіть питання для {employee_name} на NETRONIC Pulse:',
                                         call.message.chat.id,
                                         call.message.message_id)
    netronic_pulse_data[call.message.chat.id]['sent_message'] = sent_message


@bot.message_handler(func=lambda message: process_in_progress.get(message.chat.id) == 'netronic_pulse_question')
@authorized_only(user_type='users')
def handle_netronic_pulse_question(message):
    employee_name = netronic_pulse_data[message.chat.id]['employee_name']
    department = netronic_pulse_data[message.chat.id]['department']
    question = message.text

    with DatabaseConnection() as (conn, cursor):
        cursor.execute('''SELECT id
                          FROM employees
                          WHERE telegram_user_id = %s''', (message.chat.id,))
        from_user_id = cursor.fetchone()[0]

        cursor.execute('''
                       INSERT INTO netronic_pulse_questions (from_user, to_user, question)
                       VALUES (%s, %s, %s)
                       ''', (from_user_id, employee_name, question))
        conn.commit()

    scheduler.add_job(run_update_pulse_questions_in_sheet, trigger='date', run_date=datetime.datetime.now())

    bot.delete_message(message.chat.id, netronic_pulse_data[message.chat.id]['sent_message'].id)
    bot.send_message(message.chat.id,
                     f'✅ Дякуємо за ваше питання. Після модерації воно буде обговорено на наступній зустрічі '
                     f'NETRONIC Pulse.')
