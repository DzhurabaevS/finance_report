BANKS = [
    {
        "id": "abank",
        "name": "ABank",
        "reports_url": "https://abank.kg/ru/finance",
        "active": True,
    },
    {
        "id": "eldik",
        "name": "Элдик Банк",
        "reports_url": "https://eldik.kg/ru/reports",
        "active": True,
    },
    {
        "id": "mbank",
        "name": "MBank",
        "reports_url": "https://mbank.kg/reports",
        "active": True,
    },
    {
        "id": "bakai",
        "name": "Бакай Банк",
        "reports_url": "https://bakai.kg/about-us/finance/",
        "active": True,
    },
    {
        "id": "kicb",
        "name": "KICB",
        "reports_url": "https://kicb.net/about/financial-reporting/2026/",
        "active": True,
    },
    {
        "id": "capital",
        "name": "Capital Bank",
        "reports_url": "https://www.capitalbank.kg/capital/otchetnost",
        "active": True,
    },
    {
        "id": "keremet",
        "name": "Keremet Bank",
        "reports_url": "https://keremetbank.kg/ru/about/reports",
        "active": True,
    },
    {
        "id": "optima",
        "name": "Optima Bank",
        "reports_url": "https://optimabank.kg/ru/about-the-bank/reporting",
        "active": True,
    },
    {
        "id": "demirbank",
        "name": "DemirBank",
        "reports_url": "https://www.demirbank.kg/financial-institutions/finances/financial-indicators",
        "active": True,
    },
    {
        "id": "kompanion",
        "name": "Банк Компаньон",
        "reports_url": "https://www.kompanion.kg/ru/report/",
        "active": True,
    },
    {
        "id": "obank",
        "name": "O!Bank",
        "reports_url": "https://obank.kg/ru/financial-statements",
        "active": True,
    },
    {
        "id": "finca",
        "name": "FINCA Bank",
        "reports_url": "https://fincabank.kg/financials/",
        "active": True,
    },
    {
        "id": "esb",
        "name": "ЭкоИсламикБанк",
        "reports_url": "https://esb.kg/o-banke/otchety-banka",
        "active": True,
    },
    {
        "id": "dcb",
        "name": "Дос-Кредобанк",
        "reports_url": "https://www.dcb.kg/ru/about-bank/financial-performance",
        "active": True,
    },
    {
        "id": "baitushum",
        "name": "Банк Бай-Тушум",
        "reports_url": "https://www.baitushum.kg/ru/about/financial-statements/",
        "active": True,
    },
    {
        "id": "ksbc",
        "name": "Кыргызстанский коммерческий банк",
        "reports_url": "https://www.ksbc.kg/reporting/",
        "active": True,
    },
    {
        "id": "bankasia",
        "name": "Банк Азии",
        "reports_url": "https://www.bankasia.kg/ru/o-banke/finansovye-pokazateli/",
        "active": True,
    },
    {
        "id": "kkb",
        "name": "Кыргызкоммерцбанк",
        "reports_url": "https://kkb.kg/page/218",
        "active": True,
    },
    {
        "id": "eib",
        "name": "Евразийский инвестиционный банк",
        "reports_url": "https://eib.kg/finreport/month.html",
        "active": True,
    },
    {
        "id": "fkb",
        "name": "ФинансКредитБанк",
        "reports_url": "https://www.fkb.kg/financial-reports?reportType=Monthly",
        "active": True,
    },
    {
        "id": "tolubay",
        "name": "Толубай Банк",
        "reports_url": "https://www.tolubaybank.kg/index.php?option=com_content&view=article&id=39&Itemid=210&lang=ru",
        "active": True,
    },
    {
        "id": "muras",
        "name": "Мурас Банк",
        "reports_url": "https://murasbank.kg/documents",
        "active": True,
    },
    {
        "id": "alma",
        "name": "Alma Finance Bank",
        "reports_url": "https://almabank.kg/ru/about-the-bank/financial-statements",
        "active": True,
    },
    {
        "id": "bereket",
        "name": "Bereket Bank",
        "reports_url": "https://bereketbank.kg/ru/reports",
        "active": True,
    },
    {
        "id": "kylym",
        "name": "Кылым Банк",
        "reports_url": "https://www.kylymbank.kg/",
        "active": True,
    },
]

def get_all_banks():
    return BANKS

def get_active_banks():
    return [
        bank 
        for bank in BANKS
        if bank["active"]
    ]

def get_bank_by_id(bank_id):
    for bank in BANKS:
        if bank["id"] == bank_id:
            return bank