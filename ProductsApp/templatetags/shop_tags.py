import json
from django import template

register = template.Library()


@register.filter
def get_first_image(images):
    """Возвращает первую картинку из JSON-списка."""
    if not images:
        return '👕'
    try:
        img_list = json.loads(images) if isinstance(images, str) else images
        if img_list and isinstance(img_list, list):
            return img_list[0]
    except (ValueError, TypeError):
        pass
    return '👕'


@register.filter
def is_url(value):
    """Проверяет, является ли строка URL."""
    return isinstance(value, str) and (value.startswith('http') or value.startswith('/'))


@register.filter
def json_list(value):
    """Превращает JSON-строку питоновский список или возвращает пустой список."""
    if isinstance(value, list):
        return value
    try:
        return json.loads(value) if value else []
    except (ValueError, TypeError):
        return []


@register.filter(name='price_format')
def price_format(value):
    """Форматирует число с пробелами: 290000 → 290 000 so'm"""
    try:
        return f"{int(value):,}".replace(',', ' ') + " so'm"
    except (ValueError, TypeError):
        return value


@register.filter(name='format_price')
def format_price(value):
    """Alias: только число с пробелами без валюты."""
    try:
        return f'{int(value):,}'.replace(',', ' ')
    except (ValueError, TypeError):
        return value
