from app.banks.registry import get_active_banks

class CollectionManager:
    def __init__(self):
        self.banks = get_active_banks()

    def start(self, period):
        for bank in self.banks:
            print(
                f"Обработка: {bank['name']}",
                f"за {period}"
            )