#!/usr/bin/env python3
"""
Генератор глав для «Записок Мурлыкающего Философа».
Запускается ежедневно кроном. Создаёт новую главу в chapters/NN.md
и обновляет index.html (добавляет запись в CHAPTERS).
"""
import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent
CHAPTERS_DIR = REPO_ROOT / "chapters"
INDEX_FILE = REPO_ROOT / "index.html"

# Темы для глав (циклически или рандомно)
CHAPTER_THEMES = [
    ("Про пробуждение и утренний ритуал", "morning"),
    ("Про коробки и невидимые границы", "boxes"),
    ("Про птиц за окном и справедливость", "birds"),
    ("Про ветеринара и достоинство", "vet"),
    ("Про детские рисунки на холодильнике", "drawings"),
    ("Про дождь и уют", "rain"),
    ("Про ссоры и мириния", "fights"),
    ("Про новый игрушечный мышь", "toy"),
    ("Про ковер как поле битвы", "carpet"),
    ("Про запах выпечки и терпение", "baking"),
    ("Про звонки бабушки и мудрость", "grandma"),
    ("Про потерянный носок и детектив", "sock"),
    ("Про весеннее солнце и мольт", "spring"),
    ("Про гостей и личные границы", "guests"),
    ("Про ночную охоту и тишину", "night"),
    ("Про кормление и ритуалы", "feeding"),
    ("Про лучи солнца как лестницы", "sunbeams"),
    ("Про шуршание пакетов и надежда", "bags"),
    ("Про фотосессии и ванитет", "photos"),
    ("Про возраст и серые усы", "aging"),
    ("Про мечты и мурлыканье во сне", "dreams"),
    ("Про клавиатуру как трон", "keyboard"),
    ("Про пустой лоток и принципы", "litter"),
    ("Про полку над шкафом и свобода", "shelf"),
    ("Про возвращение домой и радость", "return"),
    ("Про кашлянувший крош и забота", "hairball"),
    ("Про картонный домик и архитектура", "cardboard"),
    ("Про лазерный указатель и философия", "laser"),
    ("Про мытьё окон и прозрачность", "windows"),
    ("Про первый снег и неверие", "snow"),
    ("Про рождественскую ёлку и опасность", "tree"),
]

def get_existing_chapters():
    """Считывает существующие главы из index.html"""
    if not INDEX_FILE.exists():
        return []
    content = INDEX_FILE.read_text(encoding='utf-8')
    # Ищем массив CHAPTERS = [...]
    match = re.search(r'const CHAPTERS\s*=\s*(\[[\s\S]*?\]);', content)
    if not match:
        return []
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

def get_next_chapter_number(existing):
    return len(existing) + 1

def generate_chapter_content(number, theme_title, theme_key):
    """Генерирует markdown главы через LLM (здесь — шаблон для примера).
    В продакшене здесь будет вызов Hermes API."""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Промпт для генерации
    prompt = f"""Напиши главу {number} книги "Записки Мурлыкающего Философа".

Персонаж: Маркиз — шотландский вислоухий кот, 5 лет, мудрый, ироничный, наблюдательный.
Повествование от первого лица кота.
Тон: тёплый, философский, слегка юмористический, уютный (cozy).
Тема главы: "{theme_title}".
Дата: {today}.

Структура:
- Заголовок главы (h1)
- 3-4 раздела, разделённые ***
- Внутренние монологи, наблюдения за семьёй (жена 45 лет, муж, дети)
- Кошачья логика + человеческая мудрость
- В конце — P.S. с кошачьим советом
- 1500-2500 символов
- Только markdown, без лишнего текста"""

    # Для демо вернём заглушку; в продакшене заменить на вызов API
    return f"""# Глава {number}. {theme_title}

*{today}*

Солнце легла на ковер так, будто решила остаться навсегда. Я не возражаю — мои обязанности по контролю солнечных пятен никто не отменял.

***

Сегодня тема — {theme_title.lower()}. Казалось бы, простая вещь. Но в простоте, как в пустой коробке, скрыта вся вселенная.

Моя человек сидит за столом с чашкой остывающего чая. Её пальцы касаются края кружки так же осторожно, будто это не керамика, а чьё-то доверие. Я знаю это чувство. Доверие — как шерсть на животе: гладкая, тёплая, но один неверный коготь — и остаются раны на месяцы.

Муж ушёл рано. Оставил на столе записку: *«Купи молока. Люблю»*. Я нюхнул бумагу — пахнет мужчиной, кофе и тревогой за завтрашний день. Положился на записку. Пусть полежит под моим весом. Иногда ответственность нужно придавить к столу, чтобы не улетела.

Дети в школе. Старший — с контрольной по физике. Младший — с рисунком «моя семья», где я изображен больше папы, но меньше мамы. Справедливо. Я — центр гравитации этого дома. Все вращаются вокруг меня, даже если об этом не знают.

***

Окно слегка приоткрыто. Внутрь залетает запах мокрого асфальта, жареных булок из пекарни на углу и чьей-то чужой тревоги. Птица садится на подоконник. Мы смотрим друг другу в глаза. Она — свобода. Я — выбор.

Я выбираю тёплый пол. Выбираю чашу с водой (свежей, утренней). Выбираю место рядом с ногой моей человека, когда она вечером читает книгу и случайно гладит меня за ухом, не отрываясь от строк.

В этом и есть мудрость: не в охоте на птиц. В том, чтобы знать, за что стоишь. И за кого.

***

P.S. Если солнче легла на твой живот — не вставай. Мир подождёт. Твой мурлыканье — лучший лекарь для всех, кто рядом. Включая тебя самого.
"""

def update_index_html(existing_chapters, new_chapter):
    """Обновляет массив CHAPTERS в index.html"""
    content = INDEX_FILE.read_text(encoding='utf-8')
    
    # Формируем новый массив
    all_chapters = existing_chapters + [new_chapter]
    new_array = json.dumps(all_chapters, ensure_ascii=False, indent=2)
    
    # Заменяем в файле
    new_content = re.sub(
        r'const CHAPTERS\s*=\s*\[[\s\S]*?\];',
        f'const CHAPTERS = {new_array};',
        content
    )
    
    INDEX_FILE.write_text(new_content, encoding='utf-8')

def main():
    existing = get_existing_chapters()
    next_num = get_next_chapter_number(existing)
    
    if next_num > len(CHAPTER_THEMES):
        print(f"Все {len(CHAPTER_THEMES)} тем использованы. Начинаем цикл заново или ждём новые темы.")
        return
    
    theme_title, theme_key = CHAPTER_THEMES[next_num - 1]
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f"{next_num:02d}.md"
    filepath = CHAPTERS_DIR / filename
    
    # Генерируем контент
    md_content = generate_chapter_content(next_num, theme_title, theme_key)
    
    # Сохраняем главу
    filepath.write_text(md_content, encoding='utf-8')
    print(f"Создана глава {next_num}: {filename}")
    
    # Обновляем index.html
    new_chapter = {
        "file": f"chapters/{filename}",
        "title": theme_title,
        "date": today
    }
    update_index_html(existing, new_chapter)
    print(f"index.html обновлён")
    
    # Гит коммит
    os.chdir(REPO_ROOT)
    os.system(f'git add chapters/{filename} index.html')
    os.system(f'git commit -m "feat: глава {next_num} — {theme_title}"')
    os.system('git push')
    print("Запушено в GitHub")

if __name__ == "__main__":
    main()