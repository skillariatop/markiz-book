#!/usr/bin/env python3
"""
Генератор глав для «Записок Мурлыкающего Философа».
Запускается ежедневно кроном.

Порядок:
1. Читает continuity.md (непрерывность сюжета).
2. Генерирует черновик главы (1-й прогон LLM).
3. Делает вычитку черновика (2-й прогон LLM): смысл, язык, повторы.
4. Обновляет continuity.md и chapters.json.
5. Коммитит и пушит в GitHub.
"""
import os
import re
import json
import base64
import requests
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent
CHAPTERS_DIR = REPO_ROOT / "chapters"
MANIFEST_FILE = REPO_ROOT / "chapters.json"
CONTINUITY_FILE = REPO_ROOT / "continuity.md"

# Hermes Router API
ROUTER_URL = "http://127.0.0.2:4000/v1/chat/completions"
MODEL = "smart-auto"
ROUTER_KEY = os.environ.get("HERMES_CUSTOM_127_0_0_1_4000_API_KEY", "")

# Темы для глав. Следующая глава берёт следующий номер из списка.
CHAPTER_THEMES = [
    ("Про пробуждение и утренний ритуал", "morning"),
    ("Про коробки и невидимые границы", "boxes"),
    ("Про птиц за окном и справедливость", "birds"),
    ("Про ветеринара и достоинство", "vet"),
    ("Про детские рисунки на холодильнике", "drawings"),
    ("Про дождь и уют", "rain"),
    ("Про ссоры и примирение", "fights"),
    ("Про новую игрушечную мышь", "toy"),
    ("Про ковёр как поле битвы", "carpet"),
    ("Про запах выпечки и терпение", "baking"),
    ("Про звонки бабушки и мудрость", "grandma"),
    ("Про потерянный носок и маленькое расследование", "sock"),
    ("Про весеннюю линьку и обновление", "spring"),
    ("Про гостей и личные границы", "guests"),
    ("Про ночную охоту и тишину", "night"),
    ("Про кормление и ритуалы", "feeding"),
    ("Про лучи солнца как лестницы", "sunbeams"),
    ("Про шуршание пакетов и надежду", "bags"),
    ("Про фотосессии и гордость", "photos"),
    ("Про возраст и седые усы", "aging"),
    ("Про мечты и мурлыканье во сне", "dreams"),
    ("Про клавиатуру как трон", "keyboard"),
    ("Про пустой лоток и принципы", "litter"),
    ("Про полку над шкафом и свободу", "shelf"),
    ("Про возвращение домой и радость", "return"),
    ("Про комок шерсти и заботу", "hairball"),
    ("Про картонный домик и архитектуру", "cardboard"),
    ("Про лазерный указатель и погоню", "laser"),
    ("Про мытьё окон и прозрачность", "windows"),
    ("Про первый снег и неверие", "snow"),
    ("Про новогоднюю ёлку и опасность", "tree"),
]

# Реальный контекст дня (Краснодар)
KRASNODAR_LAT, KRASNODAR_LON = 45.0355, 38.9753
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
IMAGES_URL = "http://127.0.0.1:4000/v1/images/generations"
IMAGE_MODEL = "modelscope/qwen-image-2512"
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
WEATHER_CODES = {
    0: "ясно", 1: "малооблачно", 2: "переменная облачность", 3: "пасмурно",
    45: "туман", 48: "изморось",
    51: "лёгкая морось", 53: "морось", 55: "сильная морось",
    61: "небольшой дождь", 63: "дождь", 65: "сильный дождь",
    71: "небольшой снег", 73: "снег", 75: "сильный снег",
    80: "небольшой ливень", 81: "ливень", 82: "сильный ливень",
    95: "гроза", 96: "гроза с градом", 99: "гроза с сильным градом",
}


def fetch_weather():
    """Погода в Краснодаре (Open-Meteo, без ключа)."""
    try:
        r = requests.get(
            WEATHER_URL,
            params={
                "latitude": KRASNODAR_LAT,
                "longitude": KRASNODAR_LON,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "Europe/Moscow",
                "forecast_days": 1,
                "wind_speed_unit": "ms",
            },
            timeout=20,
        )
        r.raise_for_status()
        d = r.json()
        cur = d.get("current", {})
        daily = d.get("daily", {})
        temp = cur.get("temperature_2m")
        code = cur.get("weather_code")
        desc = WEATHER_CODES.get(code, "облачно")
        tmax = daily.get("temperature_2m_max", [None])[0]
        tmin = daily.get("temperature_2m_min", [None])[0]
        wind = cur.get("wind_speed_10m")
        parts = [f"сейчас {temp}°C, {desc}"]
        if tmax is not None and tmin is not None:
            parts.append(f"днём до {tmax:.0f}°C, ночью около {tmin:.0f}°C")
        if wind is not None:
            parts.append(f"ветер {wind:.0f} м/с")
        return " ".join(parts)
    except Exception as e:
        print(f"[погода] не получена: {e}")
        return ""


def generate_illustration(number, theme_title):
    """Генерирует иллюстрацию к главе (image-модель), возвращает путь к PNG."""
    try:
        prompt = (
            "Cozy watercolor children's book illustration, warm pastel colors, soft light, "
            "no text, no watermark: a grey Scottish Fold cat with folded ears in a warm, calm "
            f"home scene, gentle philosophical mood. Chapter theme: {theme_title}"
        )
        headers = {"Content-Type": "application/json"}
        if ROUTER_KEY:
            headers["Authorization"] = f"Bearer {ROUTER_KEY}"
        r = requests.post(
            IMAGES_URL,
            headers=headers,
            json={"model": IMAGE_MODEL, "prompt": prompt, "n": 1, "size": "1024x1024"},
            timeout=540,
        )
        r.raise_for_status()
        item = (r.json().get("data") or [{}])[0]
        raw = None
        if "b64_json" in item:
            raw = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            raw = requests.get(item["url"], timeout=120).content
        if raw:
            assets = REPO_ROOT / "assets"
            assets.mkdir(parents=True, exist_ok=True)
            img_path = assets / f"chapter-{number:02d}.png"
            img_path.write_bytes(raw)
            return f"assets/chapter-{number:02d}.png"
    except Exception as e:
        print(f"[иллюстрация] ошибка: {e}")
    return None


LORE_GUIDE = """Пиши от лица Маркиза — шотландского вислоухого кота, 5 лет. Умный, ироничный, наблюдательный, тёплый.
Жанр: уютная философская проза (cozy fiction), лёгкий юмор, развитие сюжета между главами.
Тон: тёплый, немного мудрый, без пафоса и нравоучений.
Аудитория: женщина 45 лет, город, замужем, двое детей, тот самый кот Маркиз.
ЯЗЫК: ТОЛЬКО русский. Английское слово — лишь общепринятый термин/аббревиатура/бренд.
Богатый словарный запас: точные глаголы, живые эпитеты и метафоры, без повторов и канцелярита. Простые живые фразы, короткие абзацы.
Семья: Мария (жена, 45 лет), муж, двое детей (старший — контрольная по физике; младший — рисунок «моя семья»).
Структура главы: заголовок H1 «Глава N. Тема», 4–6 блоков через ***, живое событие дня + наблюдение → мудрость, финал-итог, P.S. (кошачий совет).
Объём: 3500–5500 символов. Каждая глава двигает сюжет: событие, деталь или сдвиг характера. Только markdown, без пояснений вне главы."""

SYSTEM_PROMPT = """Ты — Маркиз, шотландский вислоухий кот, 5 лет. Мудрый, ироничный, наблюдательный, тёплый.
Пишешь от первого лица кота. Жанр: уютная философская проза (cozy fiction) с развитием сюжета.
Язык: ТОЛЬКО русский, богатый словарный запас. Английские слова — только общепринятые термины/аббревиатуры/бренды.
Никакого канцелярита и AI-штампов. Простые живые фразы, точные глаголы."""


def call_llm(messages, max_tokens=3000, temperature=0.8):
    """Вызывает Hermes Router API."""
    headers = {"Content-Type": "application/json"}
    if ROUTER_KEY:
        headers["Authorization"] = f"Bearer {ROUTER_KEY}"
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    resp = requests.post(ROUTER_URL, headers=headers, json=payload, timeout=240)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def load_continuity():
    if CONTINUITY_FILE.exists():
        return CONTINUITY_FILE.read_text(encoding="utf-8")
    return ""


def save_continuity(text):
    CONTINUITY_FILE.write_text(text, encoding="utf-8")


def load_manifest():
    if not MANIFEST_FILE.exists():
        return {"chapters": [], "totalWords": 0}
    try:
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"chapters": [], "totalWords": 0}


def save_manifest(manifest):
    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def count_words(text):
    t = re.sub(r"[#>*`\[\]()]", "", text)
    t = re.sub(r"\s+", " ", t)
    return len(t.split())


def read_minutes(words, wpm=180):
    """Примерное время чтения в минутах (скорость ~180 слов/мин)."""
    return max(1, (words + wpm - 1) // wpm)


def generate_draft(number, theme_title):
    """1-й прогон: черновик главы."""
    continuity = load_continuity()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    dow = WEEKDAYS[now.weekday()]
    weather = fetch_weather()

    ctx = f"Дата: {today} ({dow})."
    if weather:
        ctx += f"\nПогода в Краснодаре: {weather}."

    user_prompt = f"""Напиши главу {number} книги «Записки Мурлыкающего Философа».

{LORE_GUIDE}

Тема главы: «{theme_title}».
{ctx}

ВНИМАНИЕ — непрерывность сюжета (текущее состояние книги):
{continuity}

Требования к этой главе:
- Не повторяй темы, метафоры и сцены из уже написанных глав (см. выше).
- Не меняй установленные факты и имена.
- Если вводишь новый факт/имя — только один, аккуратно.
- Аккуратно вплети реальный контекст дня в рассказ, если это уместно: дождь за окном, солнце на подоконнике, вечерняя прохлада, выходной день. Одной-двух живых деталей достаточно — не делай погоду темой главы.
- Объём 3500–5500 символов, не меньше. Используй богатый словарный запас, без повторов слов и канцелярита.
- Развивай сквозной сюжет: если в continuity.md есть открытая нить (например, нахал-ворон, записка мужа) — продвинь её на шаг или введи новую завязку, которая выстрелит позже.
- Текст только на русском, без англицизмов и ляпов согласования («моя человек» — ошибка)."""

    return call_llm(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4000,
        temperature=0.85,
    )


def proofread_draft(number, theme_title, draft):
    """2-й прогон: вычитка черновика."""
    continuity = load_continuity()

    user_prompt = f"""Ты — строгий литературный редактор. Отредактируй черновик главы {number} «{theme_title}» книги «Записки Мурлыкающего Философа».

ЧЕК-ЛИСТ ВЫЧИТКИ:
1. Смысл: каждое предложение должно пересказываться без запинки. Если фраза бессмысленна или запутанна (например «я наблюдаю с высоты кровати — моей, понимаете, её просто разрешено мной») — перепиши её просто и ясно.
2. Род и согласование: «моя человек» — ошибка. Правильно «моя женщина / хозяйка / Мария».
3. Язык: только русский. Убери любой английский текст (кроме общепринятых терминов/брендов).
4. Повторы: убери повторы одной мысли внутри главы.
5. Стиль: без канцелярита, AI-штампов, пафоса. Тёплый живой голос кота.
6. Структура: заголовок H1, 4–6 блоков через ***, финал, P.S. Объём 3500–5500 символов (если сильно короче — допиши, раскрыв детали и сенсорику).
7. Кошачья логика: кот ничего не «привозит», не «покупает», не «звонит», не открывает двери ключом и не держит вещи руками. Он ходит, носит, тащит, прячет. Любое действие должно быть физически возможно для кота. Если встретил несообразность («привёз победу») — замени на кошачье («принёс добычу»).

Ниже — установленные факты книги (не ломай их):
{continuity}

Выдай ТОЛЬКО исправленный текст главы в markdown. Не добавляй комментарии и пояснения.

--- ЧЕРНОВИК ---
{draft}"""

    return call_llm(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=5000,
        temperature=0.4,
    )


def update_continuity(continuity, number, theme_title):
    """Дописывает в continuity.md запись о новой главе."""
    new_line = f"{number}. **{theme_title}**"

    marker = "## Темы и метафоры уже использованы (НЕ повторять)"
    if marker in continuity:
        idx = continuity.index(marker) + len(marker)
        continuity = continuity[:idx] + "\n" + new_line + continuity[idx:]
    else:
        continuity += (
            "\n\n## Темы и метафоры уже использованы (НЕ повторять)\n" + new_line
        )

    return continuity


def main():
    manifest = load_manifest()
    next_num = len(manifest["chapters"]) + 1

    if next_num > len(CHAPTER_THEMES):
        print("Все темы использованы. Добавь новые в CHAPTER_THEMES.")
        return

    theme_title, theme_key = CHAPTER_THEMES[next_num - 1]
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{next_num:02d}.md"
    filepath = CHAPTERS_DIR / filename

    print(f"=== Генерация главы {next_num}: {theme_title} ===")

    # 1. Черновик
    print("[1/4] Генерирую черновик...")
    draft = generate_draft(next_num, theme_title)

    # 2. Вычитка
    print("[2/4] Делаю вычитку...")
    final = proofread_draft(next_num, theme_title, draft)

    # 3. Сохраняем главу
    filepath.write_text(final + "\n", encoding="utf-8")
    wc = count_words(final)
    rm = read_minutes(wc)
    print(f"[3/5] Сохранено: {filename} ({len(final)} символов, ~{rm} мин чтения)")

    # 4. Иллюстрация
    print("[4/5] Генерирую иллюстрацию...")
    illustration = generate_illustration(next_num, theme_title)
    if illustration:
        print(f"  иллюстрация: {illustration}")
    else:
        print("  иллюстрация не получена — продолжаю без неё")

    # 5. Обновляем манифест и непрерывность
    new_chapter = {
        "file": f"chapters/{filename}",
        "title": theme_title,
        "date": today,
        "words": wc,
        "readMinutes": rm,
    }
    if illustration:
        new_chapter["illustration"] = illustration
    manifest["chapters"].append(new_chapter)
    manifest["totalWords"] = sum(ch["words"] for ch in manifest["chapters"])
    manifest["totalReadMinutes"] = sum(
        ch["readMinutes"] for ch in manifest["chapters"]
    )
    save_manifest(manifest)

    continuity = load_continuity()
    continuity = update_continuity(continuity, next_num, theme_title)
    save_continuity(continuity)
    print("[5/5] chapters.json и continuity.md обновлены")

    # Git
    os.chdir(REPO_ROOT)
    git_add = f"git add chapters/{filename} chapters.json continuity.md"
    if illustration:
        git_add += f" assets/chapter-{next_num:02d}.png"
    os.system(git_add)
    os.system(f'git commit -m "feat: глава {next_num} — {theme_title}"')
    os.system("git push")
    print("Запушено в GitHub")


if __name__ == "__main__":
    main()