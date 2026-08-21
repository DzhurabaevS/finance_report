import re


class ReportExtractor:

    @staticmethod
    def clean_number(value):
        value = value.strip()
        value = value.replace("\xa0", " ")
        value = value.replace(" ", "")

        negative = (
            value.startswith("(")
            and value.endswith(")")
        )

        value = value.strip("()")

        # Убираем мусор OCR
        value = re.sub(r"[^\d.-]", "", value)

        if not value:
            return None

        try:
            number = int(value)
            return -number if negative else number
        except ValueError:
            return None

    @classmethod
    def extract_row_numbers(cls, line):
        """
        Извлекает числа из одной строки таблицы.

        Например:

        '99 104 791 75 596 359 86 129 830'

        ->
        [99104791, 75596359, 86129830]
        """

        # Число с разделителями пробелами
        pattern = r"\(?\d{1,3}(?:\s\d{3})*\)?"

        matches = re.findall(pattern, line)

        result = []

        for match in matches:
            value = cls.clean_number(match)

            if value is not None:
                result.append(value)

        return result

    def extract_financial_position(self, text):

        lines = text.splitlines()

        for i, line in enumerate(lines):
            if "Итого активы" in line:
                print("АКТИВЫ:", i, repr(line))

            if "Итого обязательства" in line:
                print("ОБЯЗАТЕЛЬСТВА:", i, repr(line))

            if "Итого капитал" in line:
                print("КАПИТАЛ:", i, repr(line))

        return {}

    def extract_income_statement(self, text):

        data = {}

        # Находим второй блок с датами.
        positions = [
            m.start()
            for m in re.finditer(
                r"31\.07\.2026",
                text
            )
        ]

        if len(positions) < 2:
            print("Таблица совокупного дохода не найдена")
            return data

        start_position = positions[1]

        table = text[start_position:]

        lines = [
            line.strip()
            for line in table.splitlines()
            if line.strip()
        ]

        numeric_rows = []

        for line in lines:

            numbers = self.extract_row_numbers(line)

            if len(numbers) >= 3:
                numeric_rows.append(numbers[:3])

        print(
            "Найдено строк доходов:",
            len(numeric_rows)
        )

        for i, row in enumerate(numeric_rows):

            if i < 20:
                print(i, row)

        return data

    def extract_ratios(self, text):

        data = {}

        patterns = {
            "K1.1": r"K1\.1.*?не более\s+20%\s+([\d.,]+)%",
            "K1.2": r"K1\.2.*?не более\s+20%\s+([\d.,]+)%",
            "K1.3": r"K1\.3.*?не более\s+30%\s+([\d.,]+)%",
            "K1.4": r"K1\.4.*?не более\s+20%\s+([\d.,]+)%",
        }

        for name, pattern in patterns.items():

            match = re.search(
                pattern,
                text,
                re.IGNORECASE | re.DOTALL
            )

            if match:

                value = match.group(1)
                value = value.replace(",", ".")

                try:
                    data[name] = float(value)
                except ValueError:
                    pass

        return data


if __name__ == "__main__":

    print("report extractor has been started")

    text_path = "ocr_text.txt"

    with open(
        text_path,
        "r",
        encoding="utf-8"
    ) as file:
        text = file.read()

    extractor = ReportExtractor()

    print("\nФИНАНСОВОЕ ПОЛОЖЕНИЕ")

    print(
        extractor.extract_financial_position(text)
    )

    print("\nСОВОКУПНЫЙ ДОХОД")

    print(
        extractor.extract_income_statement(text)
    )

    print("\nЭКОНОМИЧЕСКИЕ НОРМАТИВЫ")

    print(
        extractor.extract_ratios(text)
    )