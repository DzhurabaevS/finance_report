import os

from app.banks.registry import get_active_banks
from app.downloader.downloader import process_bank
from app.downloader.downloader import MONTH_FORMS


def parse_period(period):
    parts = period.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        raise ValueError("Период должен иметь формат 'Месяц ГГГГ'")

    month_name, year = parts[0].lower(), int(parts[1])
    for month, forms in MONTH_FORMS.items():
        if any(month_name.startswith(form[:4]) for form in forms):
            return month, year

    raise ValueError(f"Неизвестный месяц: {parts[0]}")

class CollectionManager:
    def __init__(self):
        self.banks = get_active_banks()

    def start(self, period, on_bank_start=None, on_bank_done=None):
        month, year = parse_period(period)
        output_root = "data/input"
        needs_manual_check = []

        for bank in self.banks:
            if on_bank_start:
                on_bank_start(bank)

            process_bank(
                bank,
                month,
                year,
                output_root,
                needs_manual_check,
            )

            if on_bank_done:
                bank_dir = os.path.join(output_root, bank["id"])
                files = os.listdir(bank_dir) if os.path.isdir(bank_dir) else []
                on_bank_done(bank, files)

        if needs_manual_check:
            period_root = os.path.join(output_root, f"{year:04d}-{month:02d}")
            os.makedirs(period_root, exist_ok=True)
            report_path = os.path.join(period_root, "needs_manual_check.txt")
            with open(report_path, "w", encoding="utf-8") as report:
                report.write("\n".join(needs_manual_check))

        return output_root, needs_manual_check