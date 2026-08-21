#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скачивание финансовых отчётов банков Кыргызстана за выбранный месяц.
Версия 2 — с учётом реальной структуры сайтов (проверено вручную для части банков).

Основной алгоритм для "обычных" сайтов:
    1. Идём по DOM странице сверху вниз.
    2. Запоминаем последний встреченный "заголовок года" (текст вида "2026",
       "Отчётность за 2026", "Финансовые отчеты за 2026 год" и т.п.) — это
       контекст года для всех ссылок, которые идут после него, пока не
       встретится следующий такой заголовок.
    3. Для каждой ссылки <a> смотрим на её текст: если в тексте есть
       название месяца (Январь, Февраля, Jan и т.д.) — это кандидат.
       Год кандидата: сначала пробуем найти прямо в тексте ссылки
       ("Январь 2026"), если там года нет — берём год из последнего
       заголовка (шаг 2).
    4. Если ссылка сразу ведёт на файл (.pdf/.xlsx/...) — скачиваем.
       Если ведёт на "промежуточную" страницу (как у O!Bank) — заходим
       на неё и скачиваем файлы, которые там найдём.

Особые случаи по конкретным банкам см. в словаре BANK_OVERRIDES ниже.

Зависимости:
    pip install requests beautifulsoup4
"""

import os
import re
import sys
import time
import argparse
import hashlib
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from app.banks.registry import BANKS

# ---------------------------------------------------------------------------
# ОСОБЫЕ СЛУЧАИ — проверено вручную заходом на сайты 2026-08-20.
# mode:
#   "generic"        — обычный контекстный алгоритм (по умолчанию)
#   "annual_only"     — на странице только годовые отчёты, месячных нет
#   "requires_js"     — список подгружается через JS, requests не увидит
#   "bot_blocked"     — сайт блокирует автоматические запросы
#   "kicb_year_url"   — своя страница на каждый год: .../financial-reporting/{year}/
# ---------------------------------------------------------------------------
BANK_OVERRIDES = {
    "eldik": {"mode": "annual_only", "note": "На странице есть только годовые отчёты."},
    "bakai": {"mode": "requires_js", "note": "Список отчётов рендерится через JS (React/Next.js)."},
    "demirbank": {"mode": "requires_js", "note": "Страница пустая при обычном GET — контент через JS."},
    "abank": {"mode": "bot_blocked", "note": "robots.txt сайта запрещает автоматический доступ."},
    "capital": {"mode": "bot_blocked", "note": "robots.txt сайта запрещает автоматический доступ."},
    "kompanion": {"mode": "bot_blocked", "note": "Сайт блокирует запросы по бот-детекту."},
    "kicb": {"mode": "kicb_year_url",
             "url_template": "https://kicb.net/about/financial-reporting/{year}/",
             "note": "У KICB отдельная страница на каждый год."},
}

FILE_EXTENSIONS = (".pdf",)
HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "strong", "b")

MONTH_FORMS = {
    1:  ["январь", "января", "янв", "january", "jan"],
    2:  ["февраль", "февраля", "фев", "february", "feb"],
    3:  ["март", "марта", "мар", "march", "mar"],
    4:  ["апрель", "апреля", "апр", "april", "apr"],
    5:  ["май", "мая", "may"],
    6:  ["июнь", "июня", "июн", "june", "jun"],
    7:  ["июль", "июля", "июл", "july", "jul"],
    8:  ["август", "августа", "авг", "august", "aug"],
    9:  ["сентябрь", "сентября", "сен", "сент", "september", "sep"],
    10: ["октябрь", "октября", "окт", "october", "oct"],
    11: ["ноябрь", "ноября", "ноя", "november", "nov"],
    12: ["декабрь", "декабря", "дек", "december", "dec"],
}

YEAR_RE = re.compile(r"\b(20[0-9]{2})\b")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 20


# ---------------------------------------------------------------------------
# Ввод месяца/года
# ---------------------------------------------------------------------------
def ask_month_year():
    while True:
        raw = input("Введите месяц и год отчёта (например: 07 2026 или июль 2026): ").strip()
        parts = raw.replace(",", " ").split()
        if len(parts) != 2:
            print("Нужно ввести два значения: месяц и год. Попробуйте ещё раз.")
            continue
        month_raw, year_raw = parts
        month = None
        if month_raw.isdigit():
            m = int(month_raw)
            if 1 <= m <= 12:
                month = m
        else:
            low = month_raw.lower()
            for m, forms in MONTH_FORMS.items():
                if any(low.startswith(f[:4]) for f in forms):
                    month = m
                    break
        if month is None:
            print("Не удалось распознать месяц. Введите число 1-12 или название на русском.")
            continue
        if not year_raw.isdigit() or len(year_raw) != 4:
            print("Год должен быть 4-значным числом, например 2026.")
            continue
        return month, int(year_raw)


def month_forms_for(month):
    return MONTH_FORMS[month]


def text_has_month(text, month):
    low = text.lower()
    if any(re.search(rf"(?<![a-zа-я]){re.escape(form)}(?![a-zа-я])", low)
           for form in month_forms_for(month)):
        return True
    numeric_month = f"(?:{month:02d}|{month})"
    return bool(re.search(rf"(?:20\d{{2}}[-_.]{numeric_month}|{numeric_month}[-_.]20\d{{2}})", low))


def extract_year_from_text(text):
    m = YEAR_RE.search(text)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def fetch_page(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or resp.encoding
    return resp.text


def download_file(url, dest_path):
    with requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True) as r:
        r.raise_for_status()
        chunks = r.iter_content(chunk_size=8192)
        first_chunk = next((chunk for chunk in chunks if chunk), b"")
        if not first_chunk.startswith(b"%PDF-"):
            raise ValueError("сервер вернул не PDF-файл")

        temporary_path = f"{dest_path}.part"
        try:
            with open(temporary_path, "wb") as f:
                f.write(first_chunk)
                for chunk in chunks:
                    if chunk:
                        f.write(chunk)
            os.replace(temporary_path, dest_path)
        finally:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)


def safe_filename(url, fallback_ext=".pdf"):
    name = os.path.basename(urlparse(url).path)
    if not name or "." not in name:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
        name = f"file_{digest}{fallback_ext}"
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    return name


def is_file_link(href):
    return href.lower().split("?")[0].endswith(FILE_EXTENSIONS)


# ---------------------------------------------------------------------------
# Основной контекстный парсер: заголовок года -> ссылки на месяцы
# ---------------------------------------------------------------------------
def iter_dom_in_order(soup):
    """Обходит все теги body в порядке появления в документе."""
    body = soup.body or soup
    for el in body.descendants:
        if isinstance(el, Tag):
            yield el


def find_month_candidates(html, base_url, month, year):
    """
    Возвращает список (file_or_landing_url, link_text, is_direct_file).
    Использует контекст заголовков года для ссылок без года в тексте.
    """
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    current_year_ctx = None

    for el in iter_dom_in_order(soup):
        if el.name in HEADING_TAGS:
            heading_text = el.get_text(" ", strip=True)
            y = extract_year_from_text(heading_text)
            # заголовок считается "годовым", только если это короткая строка
            # (не длинный параграф, где год мог встретиться случайно)
            if y and len(heading_text) <= 60:
                current_year_ctx = y

        elif el.name == "a" and el.has_attr("href"):
            href = el["href"].strip()
            if not href or href.startswith("javascript:") or href.startswith("#"):
                continue
            text = el.get_text(" ", strip=True)
            link_context = f"{text} {href}"
            if not link_context.strip() or not text_has_month(link_context, month):
                continue

            text_year = extract_year_from_text(link_context)
            effective_year = text_year if text_year is not None else current_year_ctx

            if effective_year is not None and effective_year != year:
                continue
            if effective_year is None:
                # нет никакого года контекста на странице вообще —
                # рискованный случай, помечаем отдельно ниже (fallback)
                continue

            abs_url = urljoin(base_url, href)
            candidates.append((abs_url, text, is_file_link(href)))

    return candidates


def find_month_candidates_no_year_context(html, base_url, month, year):
    """Ищет ссылки, в которых явно указаны и месяц, и нужный год."""
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("javascript:") or href.startswith("#"):
            continue
        text = a.get_text(" ", strip=True)
        link_context = f"{text} {href}"
        if text and text_has_month(link_context, month) and str(year) in link_context:
            abs_url = urljoin(base_url, href)
            candidates.append((abs_url, text, is_file_link(href)))
    return candidates


def collect_period_file_links(html, base_url, month, year):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("javascript:") or href.startswith("#"):
            continue
        link_context = f"{a.get_text(' ', strip=True)} {href}"
        if is_file_link(href) and text_has_month(link_context, month) and str(year) in link_context:
            abs_url = urljoin(base_url, href)
            text = a.get_text(" ", strip=True) or os.path.basename(urlparse(abs_url).path)
            results.append((abs_url, text))
    return list(dict.fromkeys(results))


def normalized_filename(bank_id, year, month, source_url, index):
    suffix = "" if index == 1 else f"_{index}"
    return f"{bank_id}_{year:04d}-{month:02d}{suffix}.pdf"


# ---------------------------------------------------------------------------
# Обработка одного банка
# ---------------------------------------------------------------------------
def download_matched(urls_and_texts, bank_dir, bank_id, month, year):
    """urls_and_texts: список (url, text) файлов для скачивания."""
    downloaded = 0
    seen_urls = set()
    for index, (file_url, text) in enumerate(urls_and_texts, start=1):
        if file_url in seen_urls:
            continue
        seen_urls.add(file_url)
        fname = normalized_filename(bank_id, year, month, file_url, index)
        dest = os.path.join(bank_dir, fname)
        try:
            download_file(file_url, dest)
            downloaded += 1
            print(f"  + {fname}  ({text})")
        except Exception as e:
            print(f"  ! Ошибка скачивания {file_url}: {e}")
        time.sleep(0.3)
    return downloaded


def process_bank(bank, month, year, out_root, needs_manual_check):
    name = bank["name"]
    bank_id = bank["id"]
    override = BANK_OVERRIDES.get(bank_id, {})
    mode = override.get("mode", "generic")

    print(f"\n=== {name} ({bank['reports_url']}) ===")

    if mode == "annual_only":
        print(f"  ! Пропуск: {override['note']}")
        needs_manual_check.append(f"{name}: {override['note']} -> {bank['reports_url']}")
        return

    if mode == "requires_js":
        print(f"  ! Пропуск: {override['note']}")
        needs_manual_check.append(
            f"{name}: {override['note']} Нужен Selenium/Playwright либо поиск внутреннего API. -> {bank['reports_url']}"
        )
        return

    if mode == "bot_blocked":
        print(f"  ! Внимание: {override['note']} Попробую всё равно, но может не получиться.")
        needs_manual_check.append(f"{name}: {override['note']} -> {bank['reports_url']}")

    url = bank["reports_url"]
    if mode == "kicb_year_url":
        url = override["url_template"].format(year=year)

    try:
        html = fetch_page(url)
    except Exception as e:
        print(f"  ! Не удалось открыть страницу: {e}")
        needs_manual_check.append(f"{name}: страница недоступна ({e}) -> {url}")
        return

    candidates = find_month_candidates(html, url, month, year)
    used_fallback = False
    if not candidates:
        # fallback: возможно на странице нет годовых заголовков вообще
        candidates = find_month_candidates_no_year_context(html, url, month, year)
        if candidates:
            used_fallback = True

    bank_dir = os.path.join(out_root, f"{year:04d}-{month:02d}", bank_id)
    os.makedirs(bank_dir, exist_ok=True)

    if not candidates:
        print("  ! Не нашли ссылок, соответствующих месяцу/году. Похоже, страница "
              "требует индивидуальной настройки (другая структура или JS).")
        needs_manual_check.append(
            f"{name}: не найдено совпадений по месяцу/году, нужна ручная проверка -> {url}"
        )
        return

    if used_fallback:
        print("  ! На странице нет явных годовых заголовков — год подтверждён только "
              "в подписи или URL ссылки. Проверьте результат вручную.")
        needs_manual_check.append(
            f"{name}: совпадение без годового заголовка -> {url}"
        )

    to_download = []          # прямые файлы
    landing_pages = []        # промежуточные страницы (как у O!Bank)

    for cand_url, text, is_direct in candidates:
        if is_direct:
            to_download.append((cand_url, text))
        else:
            landing_pages.append((cand_url, text))

    # промежуточные страницы -> заходим и ищем там файлы
    for page_url, text in landing_pages:
        try:
            sub_html = fetch_page(page_url)
        except Exception as e:
            print(f"  ! Не удалось открыть промежуточную страницу {page_url}: {e}")
            continue
        sub_files = collect_period_file_links(sub_html, page_url, month, year)
        if not sub_files:
            print(f"  ! На промежуточной странице ({text}) нет однозначного PDF за период: {page_url}")
            needs_manual_check.append(f"{name}: PDF за период не подтверждён -> {page_url}")
            continue
        to_download.extend(sub_files)

    if not to_download:
        print("  ! Совпадения найдены, но скачать файлы не удалось.")
        needs_manual_check.append(f"{name}: совпадения без файлов -> {url}")
        return

    downloaded = download_matched(to_download, bank_dir, bank_id, month, year)
    print(f"  Итого скачано: {downloaded} файл(ов).")


def main():
    parser = argparse.ArgumentParser(description="Скачивание отчётов банков КР за выбранный месяц (v2).")
    parser.add_argument("--month", type=int, help="Номер месяца (1-12)")
    parser.add_argument("--year", type=int, help="Год, например 2026")
    parser.add_argument("--out", default="data/input", help="Папка для сохранения файлов")
    parser.add_argument("--only", nargs="*", help="Ограничиться конкретными id банков (например --only mbank optima)")
    args = parser.parse_args()

    if args.month and args.year:
        month, year = args.month, args.year
    else:
        month, year = ask_month_year()

    if not 1 <= month <= 12:
        parser.error("--month должен быть числом от 1 до 12")
    if year < 2000 or year > 2100:
        parser.error("--year должен быть в диапазоне 2000-2100")

    out_root = args.out
    os.makedirs(out_root, exist_ok=True)

    needs_manual_check = []

    active_banks = [b for b in BANKS if b.get("active", True)]
    if args.only:
        active_banks = [b for b in active_banks if b["id"] in args.only]

    print(f"Будет обработано банков: {len(active_banks)}. Месяц: {month:02d}.{year}")

    for bank in active_banks:
        process_bank(bank, month, year, out_root, needs_manual_check)

    if needs_manual_check:
        period_root = os.path.join(out_root, f"{year:04d}-{month:02d}")
        report_path = os.path.join(period_root, "needs_manual_check.txt")
        os.makedirs(period_root, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(needs_manual_check))
        print(f"\nВНИМАНИЕ: по части банков не удалось точно определить/скачать файл за нужный месяц.")
        print(f"Список см. в: {report_path}")

    print(f"\nГотово. Файлы сохранены в: {out_root}")


if __name__ == "__main__":
    main()