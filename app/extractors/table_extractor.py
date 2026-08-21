import re
import subprocess
from pathlib import Path

import pymupdf


print("TABLE EXTRACTOR ЗАПУЩЕН")


class TableExtractor:

    TESSERACT = (
        r"C:\Users\sdzhurabaev\AppData\Local"
        r"\Tesseract-OCR\tesseract.exe"
    )

    LANG = "rus+eng"

    # ---------------------------------------------------------
    # PDF -> изображения
    # ---------------------------------------------------------

    def render_pages(self, pdf_path, output_dir="ocr_pages", dpi=200):

        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        document = pymupdf.open(pdf_path)

        image_paths = []

        for page_number, page in enumerate(document, start=1):

            print(f"Рендер страницы {page_number}...")

            matrix = pymupdf.Matrix(
                dpi / 72,
                dpi / 72
            )

            pix = page.get_pixmap(
                matrix=matrix,
                alpha=False
            )

            image_path = (
                output_dir /
                f"page_{page_number}.png"
            )

            pix.save(image_path)

            image_paths.append(image_path)

        document.close()

        return image_paths

    # ---------------------------------------------------------
    # Tesseract TSV
    # ---------------------------------------------------------

    def ocr_tsv(self, image_path):

        command = [
            self.TESSERACT,
            str(image_path),
            "stdout",
            "-l",
            self.LANG,
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

        if not lines:
            return []

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

            try:
                confidence = float(
                    columns[indexes["conf"]]
                )
            except ValueError:
                confidence = -1

            words.append({
                "block": columns[indexes["block_num"]],
                "paragraph": columns[indexes["par_num"]],
                "line": columns[indexes["line_num"]],

                "left": int(
                    columns[indexes["left"]]
                ),

                "top": int(
                    columns[indexes["top"]]
                ),

                "width": int(
                    columns[indexes["width"]]
                ),

                "height": int(
                    columns[indexes["height"]]
                ),

                "confidence": confidence,

                "text": text,
            })

        return words

    # ---------------------------------------------------------
    # Группировка слов в строки
    # ---------------------------------------------------------

    def group_lines(self, words):

        lines = {}

        for word in words:

            key = (
                word["block"],
                word["paragraph"],
                word["line"],
            )

            lines.setdefault(key, [])

            lines[key].append(word)

        result = []

        for words_in_line in lines.values():

            words_in_line.sort(
                key=lambda x: x["left"]
            )

            result.append(words_in_line)

        result.sort(
            key=lambda line: line[0]["top"]
        )

        return result

    # ---------------------------------------------------------
    # Нормализация текста
    # ---------------------------------------------------------

    @staticmethod
    def normalize(text):

        text = text.lower()

        text = text.replace("ё", "е")

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # ---------------------------------------------------------
    # Число
    # ---------------------------------------------------------

    @staticmethod
    def parse_number(text):

        """
        Примеры:

        99 104 791       -> 99104791
        (2 043 879)      -> -2043879
        -2 043 879       -> -2043879
        4 782 336        -> 4782336
        """

        text = text.strip()

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

    # ---------------------------------------------------------
    # Извлечение числовых групп
    # ---------------------------------------------------------

    def extract_numbers(
        self,
        words,
        gap_threshold=25
    ):

        if not words:
            return []

        groups = [
            [words[0]]
        ]

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

            if gap > gap_threshold:

                groups.append([])

            groups[-1].append(word)

        result = []

        for group in groups:

            text = " ".join(
                word["text"]
                for word in group
            )

            value = self.parse_number(text)

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

    # ---------------------------------------------------------
    # Проверка: является ли слово числом
    # ---------------------------------------------------------

    @staticmethod
    def is_number_start(text):

        return bool(
            re.match(
                r"^[\(\-]?\d",
                text
            )
        )

    # ---------------------------------------------------------
    # Поиск строки
    # ---------------------------------------------------------

    def find_exact_line(
        self,
        lines,
        target
    ):

        target = self.normalize(target)

        matches = []

        for line in lines:

            label_words = []
            number_words = []

            started_numbers = False

            for word in line:

                text = word["text"]

                if (
                    not started_numbers
                    and
                    not self.is_number_start(text)
                ):

                    label_words.append(word)

                else:

                    started_numbers = True
                    number_words.append(word)

            label = " ".join(
                word["text"]
                for word in label_words
            )

            label_normalized = self.normalize(
                label
            )

            # ВАЖНО:
            # здесь именно ==, а не "in".
            #
            # Поэтому:
            #
            # Итого обязательства
            #
            # не совпадёт с:
            #
            # Итого обязательства и капитал

            if label_normalized == target:

                numbers = self.extract_numbers(
                    number_words
                )

                matches.append({
                    "label": label,
                    "numbers": numbers,
                    "raw": " ".join(
                        word["text"]
                        for word in line
                    )
                })

        return matches

    # ---------------------------------------------------------
    # Получение первого столбца
    # ---------------------------------------------------------

    def first_value(
        self,
        lines,
        target
    ):

        matches = self.find_exact_line(
            lines,
            target
        )

        if not matches:
            return None

        numbers = matches[0]["numbers"]

        if not numbers:
            return None

        return numbers[0]["value"]

    # ---------------------------------------------------------
    # Баланс
    # ---------------------------------------------------------

    def extract_financial_position(
        self,
        all_pages
    ):

        result = {}

        targets = {
            "total_assets": "Итого активы",

            "total_liabilities":
                "Итого обязательства",

            "total_capital":
                "Итого капитал",
        }

        for field, target in targets.items():

            for page_number, lines in enumerate(
                all_pages,
                start=1
            ):

                value = self.first_value(
                    lines,
                    target
                )

                if value is not None:

                    result[field] = value

                    print(
                        f"{target}: {value}"
                    )

                    break

        return result

    # ---------------------------------------------------------
    # Совокупный доход
    # ---------------------------------------------------------

    def extract_income_statement(
        self,
        all_pages
    ):

        targets = {

            "interest_income":
                "Процентные доходы",

            "interest_expense":
                "Процентные расходы",

            "net_interest_income":
                "Чистые процентные доходы",

            "commission_income":
                "Комиссии полученные",

            "commission_expense":
                "Комиссии уплаченные",

            "net_profit":
                "Чистая прибыль (убыток) за период",
        }

        result = {}

        for field, target in targets.items():

            for lines in all_pages:

                value = self.first_value(
                    lines,
                    target
                )

                if value is not None:

                    result[field] = value

                    break

        return result

    # ---------------------------------------------------------
    # Экономические нормативы
    # ---------------------------------------------------------

    # ---------------------------------------------------------
# Экономические нормативы
# ---------------------------------------------------------

    def extract_ratios(self, all_pages):

        # Ищем только на последней странице.
        if not all_pages:
            return {}

        lines = all_pages[-1]

        result = {}

        targets = ["K1.1", "K1.2", "K1.3", "K1.4"]

        print("\n--- OCR НОРМАТИВОВ ---")

        for line in lines:

            raw = " ".join(word["text"] for word in line)

            # OCR может распознать К как кириллическую.
            normalized = raw.replace("К", "K").replace("к", "K")

            # Нас интересуют только строки с K1.x
            if "K1." not in normalized:
                continue

            print(normalized)

            # Все проценты в строке.
            percentages = re.findall(
                r"(\d+(?:[.,]\d+)?)\s*%",
                normalized
            )

            if len(percentages) < 2:
                continue

            # Какой норматив встретился.
            for target in targets:

                if target in normalized:
                    result[target] = float(
                        percentages[-1].replace(",", ".")
                    )
                    break

        return result
    # ---------------------------------------------------------
    # Главный метод
    # ---------------------------------------------------------

    def extract(self, pdf_path):

        print(
            f"\nОбработка: {pdf_path}"
        )

        image_paths = self.render_pages(
            pdf_path
        )

        all_pages = []

        for image_path in image_paths:

            print(
                f"\nOCR: {image_path.name}"
            )

            words = self.ocr_tsv(
                image_path
            )

            lines = self.group_lines(
                words
            )

            all_pages.append(lines)

        print(
            "\n=============================="
        )

        print(
            "ФИНАНСОВОЕ ПОЛОЖЕНИЕ"
        )

        financial_position = (
            self.extract_financial_position(
                all_pages
            )
        )

        print(financial_position)

        print(
            "\nСОВОКУПНЫЙ ДОХОД"
        )

        income_statement = (
            self.extract_income_statement(
                all_pages
            )
        )

        print(income_statement)

        print(
            "\nЭКОНОМИЧЕСКИЕ НОРМАТИВЫ"
        )

        ratios = self.extract_ratios(
            all_pages
        )

        print(ratios)

        return {
            "financial_position":
                financial_position,

            "income_statement":
                income_statement,

            "ratios":
                ratios,
        }


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    extractor = TableExtractor()

    pdf_path = (
        r"D:\dzhurabaev\finance_report"
        r"\kicb_july_2026.pdf"
    )

    result = extractor.extract(
        pdf_path
    )

    print(
        "\n\nФИНАЛЬНЫЙ РЕЗУЛЬТАТ:"
    )

    print(result)