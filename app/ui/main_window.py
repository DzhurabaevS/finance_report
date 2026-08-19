import tkinter as tk
from tkinter import ttk

from app.banks.registry import get_active_banks 
from app.collection.manager import CollectionManager
print("ЗАГРУЖЕН main_window.py")
class MainWindow:
    def __init__(self, root):
        self.root = root

        self.root.title("Сбор банковской отчетности")
        self.root.geometry("800x650")
        self.root.minsize(800, 550)

        self.create_widgets()

        self.collection_manager = CollectionManager()

    def create_widgets(self):
        # Заголовок

        title = ttk.Label(
            self.root,
            text="Сбор банковской отчетности",
            font=("Arial", 16, "bold")
        )

        title.pack(pady=(25,20))

        # Панель управления

        control_frame = ttk.Labelframe(
            self.root,
            text='Панель сбора отчетности',
            padding = 20
        )

        control_frame.pack(
            fill='x',
            padx=30,
            pady = 10
        )

        ttk.Label(
            control_frame,
            text="Период: "
        ).grid(
            row=0,
            column=0,
            padx=(0,10),
            pady = 10
        )

        self.month_var = tk.StringVar ()

        self.month_combobox = ttk.Combobox(
            control_frame,
            textvariable=self.month_var,
            state="readonly",
            width=20
        )

        self.month_combobox["values"] = [
            "Январь 2026",
            "Февраль 2026",
            "Март 2026",
            "Апрель 2026",
            "Май 2026",
            "Июнь 2026",
            "Июль 2026",
            "Август 2026",
            "Сентябрь 2026",
            "Октябрь 2026",
            "Ноябрь 2026",
            "Декабрь 2026"
        ]

        self.month_combobox.current(6)

        self.month_combobox.grid(
            row = 0,
            column = 1,
            padx = 10,
            pady = 10
        )

        self.start_button = ttk.Button(
            control_frame,
            text = "Начать сбор",
            command=self.start_collection
        )

        self.start_button.grid(
            row = 0,
            column = 2,
            padx = (30,0),
            pady = 10
        )

        # Статус

        status_frame = ttk.LabelFrame(
            self.root,
            text="Статус банков",
            padding=15
        )
        status_frame.pack(
            fill="both",
            expand=True,
            padx = 30,
            pady = 10
        )

        columns = (
            "bank",
            "status",
            "file"
        )

        self.tree = ttk.Treeview(
            status_frame,
            columns=columns,
            show="headings"
        )

        self.tree.heading(
            "bank",
            text="Банк"
        )

        self.tree.heading(
            "status",
            text="Статус"
        )

        self.tree.heading(
            "file",
            text="Файл"
        )

        self.tree.column(
            "bank",
            width=220
        )

        self.tree.column(
            "status",
            width=180
        )

        self.tree.column(
            "file",
            width=350
        )


        scrollbar = ttk.Scrollbar(
            status_frame,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        #Прогресс

        progress_frame = ttk.LabelFrame(
            self.root,
            text="Прогресс",
            padding=15
        )

        progress_frame.pack(
            fill="x",
            padx=30,
            pady=10
        )

        self.progress = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate"
        )

        self.progress.pack(
            fill="x",
            padx=10,
            pady=5
        )

        self.progress_label = ttk.Label(
            progress_frame,
            text="0 / 25"
        )

        self.progress_label.pack(
            pady=5
        )

        #Итог

        result_frame = ttk.LabelFrame(
            self.root,
            text="Результат",
            padding=15
        )

        result_frame.pack(
            fill="x",
            padx=30,
            pady=(5, 20)
        )

        self.result_label = ttk.Label(
            result_frame,
            text="Готов к работе"
        )

        self.result_label.pack(
            anchor="w"
        )

    def start_collection(self):
        print("КНОПКА НАЖАТА")
        period = self.month_var.get()

        if not period:
            self.result_label.config(
                text="Выберите период"
            )
            return

        self.result_label.config(
            text=f"Запуск сбора отчетности за {period}"
        )

        self.start_button.config(
            state="disabled"
        )

        self.collection_manager.start(period)

    def run(self):
        self.root.mainloop()


def run():
    root = tk.Tk()

    app = MainWindow(root)

    app.run()

