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

LORE_GUIDE = """Пиши от лица Маркиза — шотландского вислоухого кота, 5 лет. Умный, ироничный, наблюдательный, тёплый.
Жанр: уютная философская проза (cozy fiction), лёгкий юмор.
Тон: тёплый, немного мудрый, без пафоса и нравоучений.
Аудитория: женщина 45 лет, город, замужем, двое детей, тот самый кот Маркиз.
ЯЗЫК: ТОЛЬКО русский. Английское слово — лишь общепринятый термин/аббревиатура/бренд.
Без канцелярита и AI-штампов. Простые живые фразы, короткие абзацы.
Семья: Мария (жена, 45 лет), муж, двое детей (старший — контрольная по физике; младший — рисунок «моя семья»).
Структура главы: заголовок H1 «Глава N. Тема», 3–4 блока через ***, наблюдение дня → мудрость, финал-итог, P.S. (кошачий совет).
Объём: 1500–2500 символов. Только markdown, без пояснений вне главы."""

SYSTEM_PROMPT = """Ты — Маркиз, шотландский вислоухий кот, 5 лет. Мудрый, ироничный, наблюдательный, тёплый.
Пишешь от первого лица кота. Жанр: уютная философская проза (cozy fiction).
Язык: ТОЛЬКО русский. Английские слова — только общепринятые термины/аббревиатуры/бренды.
Никакого канцелярита и AI-штампов. Простые живые фразы."""


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


def generate_draft(number, theme_title):
    """1-й прогон: черновик главы."""
    continuity = load_continuity()
    today = datetime.now().strftime("%Y-%m-%d")

    user_prompt = f"""Напиши главу {number} книги «Записки Мурлыкающего Философа».

{LORE_GUIDE}

Тема главы: «{theme_title}».
Дата: {today}.

ВНИМАНИЕ — непрерывность сюжета (текущее состояние книги):
{continuity}

Требования к этой главе:
- Не повторяй темы, метафоры и сцены из уже написанных глав (см. выше).
- Не меняй установленные факты и имена.
- Если вводишь новый факт/имя — только один, аккуратно.
- Текст только на русском, без англицизмов и ляпов согласования («моя человек» — ошибка)."""

    return call_llm(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=3000,
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
6. Структура: заголовок H1, 3–4 блока через ***, финал, P.S.

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
        max_tokens=3500,
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
    print(f"[3/4] Сохранено: {filename} ({len(final)} символов, {wc} слов)")

    # 4. Обновляем манифест и непрерывность
    manifest["chapters"].append(
        {"file": f"chapters/{filename}", "title": theme_title, "date": today, "words": wc}
    )
    manifest["totalWords"] = sum(ch["words"] for ch in manifest["chapters"])
    save_manifest(manifest)

    continuity = load_continuity()
    continuity = update_continuity(continuity, next_num, theme_title)
    save_continuity(continuity)
    print("[4/4] chapters.json и continuity.md обновлены")

    # Git
    os.chdir(REPO_ROOT)
    os.system(f"git add chapters/{filename} chapters.json continuity.md")
    os.system(f'git commit -m "feat: глава {next_num} — {theme_title}"')
    os.system("git push")
    print("Запушено в GitHub")


if __name__ == "__main__":
    main()