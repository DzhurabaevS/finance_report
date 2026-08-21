import re
import subprocess
from pathlib import Path

import pymupdf


TESSERACT = (
    r"C:\Users\sdzhurabaev\AppData\Local"
    r"\Tesseract-OCR\tesseract.exe"
)

PDF_PATH = Path(
    r"D:\dzhurabaev\finance_report\kicb_july_2026.pdf"
)


def render_page(pdf_path, page_number=1, dpi=200):

    document = pymupdf.open(pdf_path)

    page = document[page_number - 1]

    matrix = pymupdf.Matrix(
        dpi / 72,
        dpi / 72
    )

    pix = page.get_pixmap(
        matrix=matrix,
        alpha=False
    )

    image_path = Path(
        f"test_page_{page_number}.png"
    )

    pix.save(image_path)

    document.close()

    return image_path


def ocr_tsv(image_path):

    command = [
        TESSERACT,
        str(image_path),
        "stdout",
        "-l",
        "rus+eng",
        "--psm",
        "6",
        "tsv",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )

    lines = result.stdout.splitlines()

    header = lines[0].split("\t")

    indexes = {
        name: i
        for i, name in enumerate(header)
    }

    words = []

    for row in lines[1:]:

        columns = row.split("\t")

        if len(columns) < len(header):
            continue

        text = columns[indexes["text"]].strip()

        if not text:
            continue

        words.append({
            "block": columns[indexes["block_num"]],
            "paragraph": columns[indexes["par_num"]],
            "line": columns[indexes["line_num"]],

            "left": int(columns[indexes["left"]]),
            "top": int(columns[indexes["top"]]),
            "width": int(columns[indexes["width"]]),

            "text": text,
        })

    return words


def group_lines(words):

    grouped = {}

    for word in words:

        key = (
            word["block"],
            word["paragraph"],
            word["line"],
        )

        grouped.setdefault(key, [])

        grouped[key].append(word)

    result = []

    for line in grouped.values():

        line.sort(
            key=lambda x: x["left"]
        )

        result.append(line)

    return result


def parse_number(text):

    negative = (
        text.startswith("(")
        or text.startswith("-")
    )

    digits = re.sub(
        r"[^\d]",
        "",
        text
    )

    if not digits:
        return None

    value = int(digits)

    if negative:
        value *= -1

    return value


def extract_numbers(words):

    """
    Объединяет:

    99 + 104 + 791

    в:

    99104791
    """

    if not words:
        return []

    groups = [
        [words[0]]
    ]

    GAP = 25

    for word in words[1:]:

        previous = groups[-1][-1]

        gap = (
            word["left"]
            -
            (
                previous["left"]
                +
                previous["width"]
            )
        )

        if gap > GAP:

            groups.append([])

        groups[-1].append(word)

    result = []

    for group in groups:

        text = " ".join(
            word["text"]
            for word in group
        )

        value = parse_number(text)

        if value is None:
            continue

        result.append({
            "value": value,
            "left": group[0]["left"],
            "right": (
                group[-1]["left"]
                +
                group[-1]["width"]
            ),
            "text": text,
        })

    return result


def find_assets(lines):

    for line in lines:

        raw = " ".join(
            word["text"]
            for word in line
        )

        normalized = (
            raw
            .lower()
            .replace("ё", "е")
        )

        if normalized.startswith("итого активы"):

            print("\nНАЙДЕНА СТРОКА:")
            print(raw)

            # Найдём слово "Итого активы"
            label_end = 0

            for i, word in enumerate(line):

                word_text = (
                    word["text"]
                    .lower()
                    .replace("ё", "е")
                )

                if word_text == "активы":

                    label_end = i + 1
                    break

            # Всё после "Итого активы"
            number_words = line[label_end:]

            numbers = extract_numbers(
                number_words
            )

            print("\nЧИСЛОВЫЕ СТОЛБЦЫ:")

            for i, number in enumerate(numbers):

                print(
                    f"{i + 1}: "
                    f"{number['text']} "
                    f"-> {number['value']} "
                    f"(X: {number['left']})"
                )

            if len(numbers) >= 2:

                print("\nПЕРВЫЕ ДВА СТОЛБЦА:")

                print(
                    "1-й:",
                    numbers[0]["value"]
                )

                print(
                    "2-й:",
                    numbers[1]["value"]
                )

            return numbers

    print("Строка 'Итого активы' не найдена")

    return []


def main():

    print("TEST: ИТОГО АКТИВЫ")

    image_path = render_page(
        PDF_PATH,
        page_number=1
    )

    print(
        f"OCR: {image_path}"
    )

    words = ocr_tsv(
        image_path
    )

    lines = group_lines(
        words
    )

    find_assets(lines)


if __name__ == "__main__":
    main()