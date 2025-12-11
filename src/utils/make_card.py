import re
import emoji

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

from config import FONT_EVOLVENTA, FONT_EVOLVENTA_BOLD, FONT_PACIFICO, FONT_NOTO, FONT_ARIAL, \
    FONT_ARIAL_BOLD, COMMENDATION_TEMPLATE_OLD, FONT_MANROPE, FONT_MANROPE_BOLD, FONT_ROBOTO_BOLD, FONT_ROBOTO, \
    COMMENDATION_TEMPLATE_NETRONIC, COMMENDATION_TEMPLATE_SKIFTECH


def draw_text(draw, text, font_size, center_position, color=(0, 0, 0), bold=False, font='primary', max_width=1200, max_rows=2):
    if not text:
        return

    from config import FONT_NOTO

    if font == 'primary':
        font_path = FONT_MANROPE_BOLD if bold else FONT_MANROPE
    elif font == 'secondary':
        font_path = FONT_ROBOTO_BOLD if bold else FONT_ROBOTO

    main_font = ImageFont.truetype(font_path, font_size)
    emoji_font = ImageFont.truetype(FONT_NOTO, font_size)

    clean_text = text.replace('\ufe0f', '')

    def split_text_with_emojis(s):
        result = []
        buffer = ''
        is_emoji_buffer = None

        for char in s:
            is_emoji = emoji.is_emoji(char)
            if is_emoji_buffer is None:
                is_emoji_buffer = is_emoji
                buffer = char
            elif is_emoji == is_emoji_buffer:
                buffer += char
            else:
                result.append((buffer, is_emoji_buffer))
                buffer = char
                is_emoji_buffer = is_emoji
        if buffer:
            result.append((buffer, is_emoji_buffer))
        return result

    def split_text_lines(text, font, max_width):
        words = text.split()
        lines = []
        current_line = words[0]
        for word in words[1:]:
            test_line = f'{current_line} {word}'
            width = draw.textbbox((0, 0), test_line, font=font)[2]
            if width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return lines

    lines = split_text_lines(clean_text, main_font, max_width)
    while len(lines) > max_rows:
        font_size -= 1
        main_font = ImageFont.truetype(font_path, font_size)
        emoji_font = ImageFont.truetype(FONT_NOTO, font_size)
        lines = split_text_lines(clean_text, main_font, max_width)

    total_height = sum(draw.textbbox((0, 0), line, font=main_font)[3] for line in lines)
    y = center_position[1] - total_height // 2
    if len(lines) == 2:
        y += 5

    for line in lines:
        chunks = split_text_with_emojis(line)
        x = center_position[0]
        total_line_width = sum(
            draw.textbbox((0, 0), chunk, font=emoji_font if is_emoji else main_font)[2] for chunk, is_emoji in chunks)
        x -= total_line_width // 2

        for chunk, is_emoji in chunks:
            fnt = emoji_font if is_emoji else main_font
            bbox = draw.textbbox((0, 0), chunk, font=fnt)
            draw.text((x, y), chunk, font=fnt, fill=color)
            x += bbox[2] - bbox[0]
        y += bbox[3]


def make_card(name, position, thank_you_text, value_text=None, from_name=None, from_position=None, branch='netronic'):
    big_font_size = 150
    small_font_size = 40

    value_text = re.sub(r'[^a-zA-Zа-яА-ЯёЁіІїЇєЄґҐ ]', '', value_text) if value_text else ''

    if branch == 'netronic':
        image_path = COMMENDATION_TEMPLATE_NETRONIC
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)

        draw_text(draw, position.upper(), small_font_size, (1000, 485), bold=True)
        draw_text(draw, name, big_font_size, (1000, 620))
        draw_text(draw, value_text, small_font_size, (1000, 785))
        draw_text(draw, thank_you_text.upper(), small_font_size, (1000, 888), bold=True)
        draw_text(draw, f'{datetime.now().strftime("%d.%m.%Y")}', small_font_size, (1737, 1200))
        draw_text(draw, from_name.upper(), small_font_size, (1000, 1230))
        draw_text(draw, from_position, small_font_size, (1000, 1305), max_width=400)

    else:
        image_path = COMMENDATION_TEMPLATE_SKIFTECH
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)

        draw_text(draw, position.upper(), small_font_size, (1023, 430), font='secondary', max_width=370)
        draw_text(draw, name, big_font_size, (1023, 610), font='secondary')
        draw_text(draw, value_text, small_font_size, (1023, 745), font='secondary')
        draw_text(draw, thank_you_text.upper(), small_font_size, (1023, 830), bold=True, font='secondary',
                  max_width=750, max_rows=3)
        draw_text(draw, f'{datetime.now().strftime("%d.%m.%Y")}', small_font_size, (460, 170), color=(217, 217, 217),
                  font='secondary')
        draw_text(draw, from_name, small_font_size, (1731, 1200), font='secondary')
        draw_text(draw, from_position, small_font_size, (1731, 1270), max_width=400, font='secondary')

    return image


def draw_text_old(draw, text, font_size, center_position, color=(0, 0, 0), bold=False):
    font_path = FONT_ARIAL_BOLD if bold else FONT_ARIAL
    font = ImageFont.truetype(font_path, font_size)

    def split_text(text, font, max_width):
        if not text:
            return []
        words = text.split()
        lines = []
        current_line = words[0]
        for word in words[1:]:
            test_line = f'{current_line} {word}'
            if draw.textbbox((0, 0), test_line, font=font)[2] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return lines

    max_width = 600
    lines = split_text(text, font, max_width)

    while len(lines) > 2:
        font_size -= 1
        font = ImageFont.truetype(font_path, font_size)
        lines = split_text(text, font, max_width)

    text_height = sum(draw.textbbox((0, 0), line, font=font)[3] for line in lines)
    y_offset = center_position[1] - text_height // 2

    if len(lines) == 2:
        y_offset -= 10

    for line in lines:
        text_bbox = draw.textbbox((0, 0), line, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        position = (center_position[0] - text_width // 2, y_offset)
        draw.text(position, line, fill=color, font=font)
        y_offset += text_bbox[3]


def make_card_old(name, position, thank_you_text, header_text='ПОДЯКА'):
    image_path = COMMENDATION_TEMPLATE_OLD
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    draw_text_old(draw, header_text, 68, (585, 115), (106, 157, 246), True)
    draw_text_old(draw, position, 16, (585, 200))
    draw_text_old(draw, name, 36, (585, 240), (57, 120, 213), True)
    draw_text_old(draw, thank_you_text, 19, (585, 300))
    draw_text_old(draw, f'{datetime.now().strftime("%d.%m.%Y")}', 14, (857, 402))

    return image


if __name__ == '__main__':
    make_card_old(
        'Прізвище Ім\'я',
        'ПОСАДА',
        'Текст подяки Текст подяки Текст подяки Текст подяки Текст подяки🥰💘'
    ).show()

    make_card(
        'Прізвище Ім\'я',
        'Product Manager Military',
        'Текст подяки Текст подяки Текст подяки Текст подяки Текст подяки🥰💘',
        '🎯Відповідальність і проактивність',
        'Від Прізвище Ім\'я', 'Від Посада', branch='skiftech'
    ).show()
