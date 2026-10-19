# Проверка и упаковка навыка GigaCowork в архив для «Загрузить файл навыка».
# Вход: папка <BASE>/<SLUG>/ с файлом SKILL.md и (по желанию) папкой Референсы/.
# Выход: <BASE>/<SLUG>.zip; имена файлов в архиве — в UTF-8.
# Только стандартная библиотека Python.

import os
import re
import zipfile

SLUG = "<slug>"      # имя папки навыка латиницей, например "lead-intake"
BASE = "/session"    # рабочая папка задачи

GENERIC_WORDS = ("помоги", "сделай", "расскажи")
REQUIRED = ("category", "version", "name", "description")


def read_frontmatter(text):
    """Возвращает (метаданные, тело). Поддерживает строки key: value и продолжения с отступом."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    meta, key = {}, None
    for line in text[3:end].splitlines():
        if not line.strip():
            continue
        if line[:1] in (" ", "\t") and key:
            meta[key] += " " + line.strip()
            continue
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            meta[key] = m.group(2).strip()
    for k, v in meta.items():
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            meta[k] = v[1:-1]
    body = text[end + 4:]
    return meta, body


def check(src):
    errors, warnings = [], []
    skill_path = os.path.join(src, "SKILL.md")
    if not os.path.isfile(skill_path):
        return [f"нет файла {skill_path}"], warnings
    with open(skill_path, encoding="utf-8") as f:
        text = f.read()
    meta, body = read_frontmatter(text)
    if meta is None:
        return ["SKILL.md должен начинаться с блока метаданных между строками ---"], warnings

    for key in REQUIRED:
        if not meta.get(key):
            errors.append(f"нет поля «{key}» в метаданных")
    category = meta.get("category", "")
    if category and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", category):
        errors.append(f"category «{category}»: только строчные латинские буквы и цифры через дефис, значение из списка платформы")
    version = meta.get("version", "")
    if version and not version.isdigit():
        errors.append(f"version «{version}»: нужно целое число")
    description = meta.get("description", "")
    if description:
        if len(description) > 1024:
            errors.append(f"description длиной {len(description)} знаков: сократите до 1024")
        elif len(description) < 60:
            warnings.append("description короче 60 знаков: добавьте триггеры «Используйте при запросах «…»»")
        low = description.lower()
        for word in GENERIC_WORDS:
            if re.search(rf"«\s*{word}\s*»", low):
                warnings.append(f"в description триггер «{word}» без объекта — замените конкретным, например «{word} отчёт»")
    if "Анти-триггеры" not in body and "Не использовать" not in body:
        warnings.append("нет раздела «Анти-триггеры» или «Не использовать»")
    if "Степень свободы" not in body:
        warnings.append("не указана степень свободы")

    mentioned = {n for n in re.findall(r"Референсы/([^\s`»)\]]+)", body) if "<" not in n and ">" not in n}
    ref_dir = os.path.join(src, "Референсы")
    present = set()
    if os.path.isdir(ref_dir):
        for root, _, files in os.walk(ref_dir):
            for name in files:
                present.add(os.path.relpath(os.path.join(root, name), ref_dir).replace(os.sep, "/"))
    for name in sorted(mentioned - present):
        errors.append(f"SKILL.md ссылается на Референсы/{name}, а файла нет")
    for name in sorted(present - mentioned):
        warnings.append(f"файл Референсы/{name} не упомянут в SKILL.md — агент не узнает, когда его читать")
    return errors, warnings


def pack(src, out):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(src):
            for name in sorted(files):
                path = os.path.join(root, name)
                z.write(path, os.path.relpath(path, src).replace(os.sep, "/"))


src = os.path.join(BASE, SLUG)
errors, warnings = check(src)
for w in warnings:
    print("Предупреждение:", w)
if errors:
    for e in errors:
        print("Ошибка:", e)
    print("Архив не собран — исправьте ошибки и запустите снова.")
else:
    out = os.path.join(BASE, SLUG + ".zip")
    pack(src, out)
    print("Готово:", out)
    print("Загрузка: Навыки → Создать навык → Загрузить файл навыка.")
