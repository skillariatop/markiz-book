#!/usr/bin/env python3
"""
Генератор глав для «Записок Мурлыкающего Философа».
Запускается ежедневно кроном. Создаёт новую главу в chapters/NN.md
и обновляет chapters.json (манифест глав).
"""
import os
import re
import json
import requests
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent
CHAPTERS_DIR = REPO_ROOT / "chapters"
MANIFEST_FILE = REPO_ROOT / "chapters.json"

# Hermes Router API
ROUTER_URL = "http://127.0.0.2:4000/v1/chat/completions"
# Используем smart-auto — роутер сам выберет strong/code тир
MODEL = "smart-auto"

# API ключ для роутера (из .env)
ROUTER_KEY = os.environ.get("HERMES_CUSTOM_127_0_0_1_4000_API_KEY", "")

# Темы для глав
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

def load_manifest():
    """Загружает манифест глав из chapters.json"""
    if not MANIFEST_FILE.exists():
        return {"chapters": [], "totalWords": 0}
    try:
        return json.loads(MANIFEST_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {"chapters": [], "totalWords": 0}

def save_manifest(manifest):
    """Сохраняет манифест глав"""
    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

def count_words(text):
    """Подсчёт слов в тексте (без markdown-разметки)"""
    text = re.sub(r'[#>*`\[\]()]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return len(text.split())

def get_next_chapter_number(manifest):
    return len(manifest["chapters"]) + 1

def call_llm(prompt: str, max_tokens: int = 3000) -> str:
    """Вызывает Hermes Router API для генерации главы."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ROUTER_KEY}"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Ты — Маркиз, шотландский вислоухий кот, 5 лет. Мудрый, ироничный, наблюдательный, тёплый. Пишешь от первого лица кота. Тон: уютный, философский, слегка юмористический (cozy fiction). Язык: ТОЛЬКО русский. Английские слова — только общепринятые термины/аббревиатуры/бренды."
            },
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.8,
        "stream": False
    }
    try:
        resp = requests.post(ROUTER_URL, headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Ошибка вызова LLM: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise

def generate_chapter_content(number, theme_title, theme_key):
    """Генерирует markdown главы через LLM."""
    today = datetime.now().strftime('%Y-%m-%d')
    
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
- Только markdown, без лишнего текста
- ТОЛЬКО на русском языке"""

    return call_llm(prompt)

def main():
    manifest = load_manifest()
    existing_chapters = manifest["chapters"]
    next_num = get_next_chapter_number(manifest)
    
    if next_num > len(CHAPTER_THEMES):
        print(f"Все {len(CHAPTER_THEMES)} тем использованы. Начинаем цикл заново или ждём новые темы.")
        return
    
    theme_title, theme_key = CHAPTER_THEMES[next_num - 1]
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f"{next_num:02d}.md"
    filepath = CHAPTERS_DIR / filename
    
    print(f"Генерирую главу {next_num}: {theme_title}...")
    md_content = generate_chapter_content(next_num, theme_title, theme_key)
    
    filepath.write_text(md_content, encoding='utf-8')
    word_count = count_words(md_content)
    print(f"Создана глава {next_num}: {filename} ({len(md_content)} символов, {word_count} слов)")
    
    new_chapter = {
        "file": f"chapters/{filename}",
        "title": theme_title,
        "date": today,
        "words": word_count
    }
    
    # Обновляем манифест
    manifest["chapters"].append(new_chapter)
    manifest["totalWords"] = sum(ch.get("words", 0) for ch in manifest["chapters"])
    save_manifest(manifest)
    print(f"chapters.json обновлён (всего глав: {len(manifest['chapters'])}, слов: {manifest['totalWords']})")
    
    # Git commit & push
    os.chdir(REPO_ROOT)
    os.system(f'git add chapters/{filename} chapters.json')
    os.system(f'git commit -m "feat: глава {next_num} — {theme_title}"')
    os.system('git push')
    print("Запушено в GitHub")

if __name__ == "__main__":
    main()