from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import re
import logging
import os

# Настройка логирования
if not os.path.exists('logs'):
    os.makedirs('logs')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CRPT-TURON')

from ClientCryptAPI import ClientCryptAPI
from ClientLegacyAPI import ClientLegacyAPI
from ClientTrueAPI import ClientTrueAPI
from DBClient import ClientDB
from tkcalendar import DateEntry  # Импортируем DateEntry


class Main:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CRPT-TURON")
        self.root.geometry("900x500")

        # Индикатор подключения
        self.connection_indicator = ttk.Label(self.root, text="●", foreground="red", font=("Arial", 16)) # Added connection indicator
        self.connection_indicator.pack(pady=5) # Added connection indicator
        self.connection_status_label = ttk.Label(self.root, text="Статус подключения: Не подключено", foreground="red")
        self.connection_status_label.pack(pady=10)

        # Инициализация API-клиентов и БД
        self.client_db = ClientDB("main.db")
        self.participant_id = self.client_db.get_inn()  # Это УНН

        db_param = ["PathTrueAPI", "PathCryptAPI", "PathLegacyAPI"]
        api_urls = {field: self.client_db.get_setting_by_field(field)[0][0] for field in db_param}
        self.true_api_client = ClientTrueAPI(api_urls["PathTrueAPI"])
        self.crypt_api_client = ClientCryptAPI(api_urls["PathCryptAPI"])
        self.legacy_api_client = ClientLegacyAPI(api_urls["PathLegacyAPI"], self.client_db)        

        # Фрейм для выбора сертификата
        cert_frame = ttk.LabelFrame(self.root, text="Выбор сертификата", padding=10)
        cert_frame.pack(fill="x", padx=10, pady=5)

        # Комбобокс для выбора сертификата
        self.cert_var = tk.StringVar()
        self.combo = ttk.Combobox(
            cert_frame, 
            textvariable=self.cert_var,
            width=70,
            state="readonly"
        )
        self.combo.pack(fill="x")

        # Кнопка подключения
        self.connect_button = ttk.Button(
            self.root,
            text="Подключиться",
            command=self.on_connect
        )
        self.connect_button.pack(pady=10)

        # фрейм для отображения баланса
        balance_frame = ttk.LabelFrame(self.root, text="Информация о балансе", padding=10)
        balance_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Метки для отображения информации о балансе
        self.balance_labels = {
            'balance': ttk.Label(balance_frame, text="Баланс: "),
            'contractId': ttk.Label(balance_frame, text="Номер контракта: "),
            'organisationId': ttk.Label(balance_frame, text="Код организации: "),
            'productGroupId': ttk.Label(balance_frame, text="Группа продуктов: ")
        }
        for label in self.balance_labels.values():
            label.pack(anchor='w', pady=2)

        # Загружаем сертификаты
        self.cert_list = []
        result = self.crypt_api_client.load_certificates()
        if isinstance(result, list):  # Проверяем, является ли result списком
            self.cert_list = result
        self.fill_combobox()

        # Добавляем переменные для хранения текущего состояния
        self.current_key_id = None
        self.current_cert_data = None
        self.current_token = None

        # Кнопка для обновления баланса
        self.update_balance_button = ttk.Button(
            self.root,
            text="Обновить баланс",
            command=self.on_update_balance_button_click
        )
        self.update_balance_button.pack(pady=10)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10, fill='x', padx=20)

        # Кнопка Настройки
        self.settings_button = ttk.Button(
            button_frame,
            text="Настройки",
            command=self.open_settings_window
        )
        self.settings_button.pack(side=tk.LEFT, padx=5)

        # Кнопка Устройства
        self.devices_button = ttk.Button(
            button_frame,
            text="Устройства",
            command=self.open_devices_window
        )
        self.devices_button.pack(side=tk.LEFT, padx=5)

        # Кнопка "Проверить подключение"
        self.check_connection_button = ttk.Button(
            button_frame,
            text="Проверить подключение",
            command=self.check_connection
        )
        self.check_connection_button.pack(side=tk.LEFT, padx=5)

        # Кнопка "Отправить КМ"
        self.send_km_button = ttk.Button(
            button_frame,
            text="Отправить КМ",
            command=self.open_send_km_dialog
        )
        self.send_km_button.pack(side=tk.LEFT, padx=5)

        # Кнопка "Отправить агрегацию"
        self.send_aggregation_button = ttk.Button(
            button_frame,
            text="Отправить агрегацию",
            command=self.send_aggregation
        )
        self.send_aggregation_button.pack(side=tk.LEFT)  # Размещаем справа от кнопки проверки
        
        # Кнопка "История действий"
        self.history_button = ttk.Button(
            button_frame,
            text="История действий",
            command=self.show_history
        )
        self.history_button.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(self.root, text="") # Added status label
        self.status_label.pack(pady=5) # Added status label

    def fill_combobox(self):
        """Заполняет комбобокс данными сертификатов"""
        cert_list = []
        for cert in self.cert_list:
            alias = cert.get('alias', '').upper()
            # изменяем идентификаторы на более читаемые
            alias = alias.replace("1.2.860.3.16.1.1=", "INN=")
            alias = alias.replace("1.2.860.3.16.1.2=", "PINFL=")

            # Извлекаем нужные поля
            vo = {
                'serialNumber': self._get_x500_val(alias, "SERIALNUMBER"),
                'validFrom': self._get_x500_val(alias, "VALIDFROM"),
                'validTo': self._get_x500_val(alias, "VALIDTO"),
                'CN': self._get_x500_val(alias, "CN"),
                'TIN': self._get_x500_val(alias, "INN") or self._get_x500_val(alias, "UID"),
                'O': self._get_x500_val(alias, "O"),
                'T': self._get_x500_val(alias, "T")
            }

            # Формируем строку для отображения
            display_string = f"{vo['O']} - {vo['CN']} ({vo['TIN']})"
            cert_list.append(display_string)

        self.combo['values'] = cert_list
        if cert_list:
            self.combo.set(cert_list[0])

    @staticmethod
    def _get_x500_val(x500name, field):
        """Извлекает значение поля из строки X500Name"""
        field_match = re.search(f"{field}=([^,]+)", x500name)
        return field_match.group(1) if field_match else ""

    def on_connect(self):
        """Обработчик нажатия кнопки подключения"""
        # Деактивируем кнопку на время подключения
        self.connect_button.config(state="disabled")
        self.update_status("Выполняется подключение...")
        logger.info("Начата процедура подключения")

        try:
            # Изменяем индикатор на "в процессе"
            self.connection_indicator.config(text="●", foreground="orange")
            self.connection_status_label.config(text="Статус: Подключение...", foreground="orange")
            self.root.update_idletasks()  # Обновляем интерфейс

            logger.debug("Запрос данных для аутентификации")
            data_to_sign = self.true_api_client.auth_get()
            selected_index = self.combo.current()

            if selected_index == -1:
                logger.error("Попытка подключения без выбора сертификата")
                raise Exception("Сертификат не выбран")

            self.crypt_api_client.set_selected_cert_index(selected_index)
            logger.debug(f"Выбран сертификат с индексом {selected_index}")

            self.update_status("Подписываем данные...")
            logger.debug("Начато подписание данных")
            signed_data = self.crypt_api_client.sign_data(data_to_sign, self.cert_list)
            logger.debug("Данные успешно подписаны")

            self.update_status("Авторизация...")
            logger.debug("Отправка запроса авторизации")
            self.true_api_client.auth_post(signed_data)
            logger.info("Авторизация успешно выполнена")

            # Успешное подключение
            self.connection_indicator.config(text="●", foreground="green")
            self.connection_status_label.config(text="Статус: Подключено", foreground="green")
            self.update_status("Подключение выполнено успешно")
            logger.info("Подключение выполнено успешно")

            # Получаем баланс после подключения
            self.on_update_balance_button_click()

        except Exception as e:
            self.connection_indicator.config(text="●", foreground="red")
            self.connection_status_label.config(text="Статус: Ошибка", foreground="red")
            self.update_status(f"Ошибка подключения: {str(e)}", error=True)
            logger.error(f"Ошибка подключения: {str(e)}", exc_info=True)
            messagebox.showerror("Ошибка подключения", str(e))
        finally:
            # Восстанавливаем кнопку
            self.connect_button.config(state="normal")
            logger.debug("Кнопка подключения восстановлена")

    def run(self):
        self.root.mainloop()

    def on_update_balance_button_click(self):
        """Обработчик нажатия кнопки обновления баланса"""
        self.update_balance_button.config(state="disabled")
        self.update_status("Получение данных о балансе...")

        try:
            balance_info = self.true_api_client.update_balance()  # Вызов метода обновления баланса

            if not balance_info:
                self.update_status("Не удалось получить информацию о балансе", error=True)
                return

            self.update_status("Обновление временных групп продуктов...")
            self.client_db.clear_tmp_product_group()

            # Перебираем balance_info и заполняем tmp_product_group
            for item in balance_info:
                product_group_id = item["productGroupId"]
                product_groups = self.client_db.get_product_group_data()  # Получаем product_groups из базы данных
                # Находим соответствующую запись в product_group
                for group in product_groups:
                    if group[0] == product_group_id:  # group[0] - это id из product_group
                        self.client_db.insert_into_tmp_product_group(group)

            # Обновляем метки на форме с использованием данных из balance_info
            self.write_balance_in_form(balance_info)
            self.update_status("Данные о балансе обновлены")

        except Exception as e:
            self.update_status(f"Ошибка при обновлении баланса: {str(e)}", error=True)
            messagebox.showerror("Ошибка обновления баланса", str(e))
        finally:
            self.update_balance_button.config(state="normal")

    def write_balance_in_form(self, balance_info):
        """Обновляет отображение баланса в интерфейсе"""
        total_balance = balance_info[0]['balance']
        sumy = total_balance // 100
        tiyn = total_balance % 100

        # Форматируем сумму с разделителями тысяч для лучшей читаемости
        formatted_sum = f"{sumy:,}".replace(",", " ")

        self.balance_labels['balance'].config(
            text=f"{formatted_sum} сумов {tiyn:02d} тийинов"
        )

        self.balance_labels['contractId'].config(
            text=balance_info[0]['contractId']
        )

        self.balance_labels['organisationId'].config(
            text=balance_info[0]['organisationId']
        )

        product_group_id = balance_info[0]['productGroupId']
        product_group_name = self.client_db.get_product_group_name(product_group_id)

        self.balance_labels['productGroupId'].config(
            text=product_group_name if product_group_name else "Не определено"
        )

    def update_status(self, message, error=False):
        """Updates the status label with a message."""
        color = "red" if error else "black"
        self.status_label.config(text=message, foreground=color)
        self.root.update_idletasks()
        # Логируем сообщение
        if error:
            logger.error(message)
        else:
            logger.info(message)
    
    def show_history(self):
        """Открывает окно с историей действий из лог-файла"""
        history_window = tk.Toplevel(self.root)
        history_window.title("История действий")
        history_window.geometry("800x500")
        
        # Устанавливаем окно как модальное
        history_window.transient(self.root)
        history_window.grab_set()
        
        # Создаем текстовое поле для отображения истории
        history_text = tk.Text(history_window, wrap=tk.WORD, font=("Courier", 10))
        history_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Добавляем скроллбар
        scrollbar = ttk.Scrollbar(history_text, command=history_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        history_text.config(yscrollcommand=scrollbar.set)
        
        # Загружаем содержимое лог-файла
        try:
            with open('logs/app.log', 'r', encoding='utf-8') as file:
                log_content = file.read()
                history_text.insert(tk.END, log_content)
                history_text.config(state=tk.DISABLED)  # Делаем только для чтения
        except FileNotFoundError:
            history_text.insert(tk.END, "История еще не создана.")
            history_text.config(state=tk.DISABLED)
        
        # Кнопка закрытия
        close_button = ttk.Button(
            history_window,
            text="Закрыть",
            command=history_window.destroy
        )
        close_button.pack(pady=10)


    def check_connection(self):
        """Проверяет соединение с устройством и товарной группой."""
        selected_device_name, extension_name = self.open_device_selection_window()  # Получаем выбранные значения

        if not selected_device_name or not extension_name:
            messagebox.showwarning("Предупреждение", "Пожалуйста, выберите устройство и товарную группу.")
            return

        # Получаем токен устройства по его имени
        device_token = self.client_db.get_device_token(selected_device_name)

        if device_token is None:
            messagebox.showerror("Ошибка", "Не удалось получить токен для выбранного устройства.")
            return

        # Получаем значение товарной группы по имени
        extension_value = self.client_db.get_product_group_code_by_name(extension_name)

        if extension_value is None:
            messagebox.showerror("Ошибка", "Не удалось получить значение товарной "
                                           "группы для выбранной группы продукции.")
            return

        # Проверяем соединение
        result = self.legacy_api_client.check_connection(device_token, extension_value)
        messagebox.showinfo("Успех", f"Соединение проверено: {result}")

    def open_device_selection_window(self):
        """Создает модальное окно для выбора активного устройства и товарной группы."""
        device_selection_window = tk.Toplevel(self.root)  # Создаем новое окно
        device_selection_window.title("Выбор устройства и группы продукции")
        device_selection_window.geometry("300x200")

        # Устанавливаем окно как модальное
        device_selection_window.transient(self.root)
        device_selection_window.grab_set()

        # Получаем активные устройства
        active_devices = self.client_db.get_active_devices()

        tk.Label(device_selection_window, text="Выберите устройство:").pack(pady=5)  # Метка для выбора устройства
        selected_device = tk.StringVar()
        device_dropdown = ttk.Combobox(device_selection_window, textvariable=selected_device)
        device_dropdown['values'] = [device['name'] for device in active_devices]
        device_dropdown.pack(pady=10)

        tk.Label(device_selection_window, text="Выберите товарную группу:").pack(pady=5)  # Метка для выбора ТГ
        selected_extension = tk.StringVar()
        extension_dropdown = ttk.Combobox(device_selection_window, textvariable=selected_extension)
        extensions = self.client_db.get_all_tmp_product_group_names()  # Получаем доступные товарные группы
        extension_dropdown['values'] = extensions  # Заполняем выпадающий список
        extension_dropdown.pack(pady=10)

        # Кнопка для подтверждения выбора
        confirm_button = ttk.Button(device_selection_window, text="Подтвердить", command=lambda: self.confirm_device_selection(selected_device.get(), selected_extension.get(), device_selection_window))
        confirm_button.pack(pady=10)

        # Ожидаем закрытия окна
        self.root.wait_window(device_selection_window)

        # Возвращаем выбранные значения
        return selected_device.get(), selected_extension.get()

    @staticmethod
    def confirm_device_selection(device_name, extension_name, window):
        """Подтверждает выбор устройства и закрывает окно."""
        if not device_name:
            messagebox.showwarning("Предупреждение", "Пожалуйста, выберите устройство.")
            return

        if not extension_name:
            messagebox.showwarning("Предупреждение", "Пожалуйста, выберите товарную группу.")
            return

        # Закрываем окно
        window.destroy()

    def send_aggregation(self):
        production_order_id = tk.simpledialog.askstring("Идентификатор производственного заказа",
                                                        "Идентификатор производственного заказа:")
        aggregation_unit_capacity = tk.simpledialog.askstring("Вместимость агрегированной единицы",
                                                              "Введите Вместимость агрегированной единицы:")
        # Открываем диалог выбора файла
        file_path = filedialog.askopenfilename(
            title="Выберите JSON файл",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not file_path:
            messagebox.showwarning("Предупреждение", "Файл не выбран.")
            return

        try:
            # Загружаем данные из выбранного JSON файла
            data = self.get_data_from_json(file_path, production_order_id, aggregation_unit_capacity)

            # Открываем окно выбора устройства и товарной группы
            selected_device_name, extension_name = self.open_device_selection_window()  # Получаем выбранные значения

            # Получаем токен устройства по его имени
            device_token = self.client_db.get_device_token(selected_device_name)

            if device_token is None:
                messagebox.showerror("Ошибка", "Не удалось получить токен для выбранного устройства.")
                return

            # Получаем значение товарной группы по имени
            extension = self.client_db.get_product_group_code_by_name(extension_name)

            if extension is None:
                messagebox.showerror("Ошибка", "Не удалось получить значение товарной "
                                               "группы для выбранной группы продукции.")
                return

            # Отправляем агрегацию
            result = self.legacy_api_client.send_aggregation(data, extension, device_token)
            report_id = result.get("reportId")
            messagebox.showinfo("Успех", f"Отчет успешно отправлен. ID отчета: {report_id}")

        except json.JSONDecodeError:
            messagebox.showerror("Ошибка", "Ошибка при загрузке JSON файла, проверьте формат.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def extract_sntins_and_serial_numbers(self, data):
        """Извлекает значения sntins и unitSerialNumber из структуры данных."""
        aggregation_units = []

        for task_mark in data.get('TaskMarks', []):
            for barcode_group in task_mark.get('Barcodes', []):
                if barcode_group.get('level') == 1:
                    unit_serial_number = barcode_group['Barcode']  # Получаем unitSerialNumber
                    child_barcodes = [child['Barcode'].split('\u001d')[0] for
                                      child in barcode_group.get('ChildBarcodes', []) if child.get('level') == 0]

                    # Добавляем агрегированную единицу, если есть дочерние штрих-коды
                    if child_barcodes:
                        aggregation_units.append({
                            "unitSerialNumber": unit_serial_number,
                            "sntins": child_barcodes
                        })

                # Обрабатываем дочерние группы, если они есть
                for child in barcode_group.get('ChildBarcodes', []):
                    if isinstance(child, dict) and 'ChildBarcodes' in child:
                        aggregation_units.extend(self.extract_sntins_and_serial_numbers(
                            {'TaskMarks': [{'Barcodes': [child]}]}))

        return aggregation_units

    def get_data_from_json(self, json_file, production_order_id, aggregation_unit_capacity):
        """Формирует JSON-данные для создания отчета об агрегации КМ и возвращает их."""

        # Считываем данные из JSON файла
        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Извлекаем агрегированные единицы
        aggregation_units = self.extract_sntins_and_serial_numbers(data)

        # Формируем итоговые данные
        request_data = {
            "participantId": self.participant_id,
            # "productionLineId": data.get("productionLineId"),
            "productionOrderId": production_order_id,
            # "dateDoc": data.get("dateDoc"),
            "aggregationUnits": []
        }

        # Обрабатываем массив единиц агрегации
        for unit in aggregation_units:
            aggregation_unit = {
                "aggregatedItemsCount": len(unit['sntins']),  # Подсчитываем количество sntins
                "aggregationType": "AGGREGATION",
                "aggregationUnitCapacity": int(aggregation_unit_capacity),
                "sntins": unit['sntins'],  # Используем извлеченные sntins
                "unitSerialNumber": unit['unitSerialNumber']  # Используем извлеченный unitSerialNumber
            }
            request_data["aggregationUnits"].append(aggregation_unit)

        return request_data

    def open_settings_window(self):
        """Создает модальное окно для работы с таблицей Setting."""
        settings_window = tk.Toplevel(self.root)  # Создаем новое окно
        settings_window.title("Настройки")
        settings_window.geometry("500x400")

        # Устанавливаем окно ак модальное
        settings_window.transient(self.root)  # Устанавливаем родительское окно
        settings_window.grab_set()  # Блокируем взаимодействие с родительским окном

        # Пля для ввода данных
        tk.Label(settings_window, text="Путь к API криптовровайдера (E-IMZO):").pack(pady=5)
        self.path_crypt_api_entry = tk.Entry(settings_window, width=50)
        self.path_crypt_api_entry.pack(pady=5)

        tk.Label(settings_window, text="Адрес сервера TrueAPI:").pack(pady=5)
        self.path_true_api_entry = tk.Entry(settings_window, width=50)
        self.path_true_api_entry.pack(pady=5)

        tk.Label(settings_window, text="Адрес сервера LegacyAPI:").pack(pady=5)
        self.path_legacy_api_entry = tk.Entry(settings_window, width=50)
        self.path_legacy_api_entry.pack(pady=5)

        tk.Label(settings_window, text="OMS ID:").pack(pady=5)
        self.oms_id_entry = tk.Entry(settings_window, width=50)
        self.oms_id_entry.pack(pady=5)

        tk.Label(settings_window, text="ИНН организации (9 цифр):").pack(pady=5)
        self.inn_entry = tk.Entry(settings_window, width=50)
        self.inn_entry.pack(pady=5)

        # Кнопка для сохранения изменений
        save_button = ttk.Button(settings_window, text="Сохранить", command=self.save_settings)
        save_button.pack(pady=10)

        # Загрузка текущих данных из таблицы Setting
        self.load_current_settings()

        # Ожидаем закрытия модального окна
        self.root.wait_window(settings_window)

    def load_current_settings(self):
        """Загружает текущие настройки из таблицы Setting."""
        settings = self.client_db.get_current_settings()
        if settings:
            self.path_crypt_api_entry.insert(0, settings['PathCryptAPI'])
            self.path_true_api_entry.insert(0, settings['PathTrueAPI'])
            self.path_legacy_api_entry.insert(0, settings['PathLegacyAPI'])
            self.oms_id_entry.insert(0, settings['omsId'])
            self.inn_entry.insert(0, settings['INN'])

    def save_settings(self):
        """Сохраняет настройки в таблицу Setting."""
        settings = {
            'PathCryptAPI': self.path_crypt_api_entry.get(),
            'PathTrueAPI': self.path_true_api_entry.get(),
            'PathLegacyAPI': self.path_legacy_api_entry.get(),
            'omsId': self.oms_id_entry.get(),
            'INN': self.inn_entry.get()
        }

        self.client_db.update_setting(settings)

        messagebox.showinfo("Успех", "Настройки сохранены!")

    def open_devices_window(self):
        """Создает модальное окно для работы с таблицей Devices."""
        devices_window = tk.Toplevel(self.root)  # Создаем новое окно
        devices_window.title("Устройства")
        devices_window.geometry("600x400")

        # Устанавливаем окно как модальное
        devices_window.transient(self.root)
        devices_window.grab_set()

        # Создаем таблицу для отображения устройств
        columns = ("name", "token", "active")
        self.devices_tree = ttk.Treeview(devices_window, columns=columns, show='headings')
        self.devices_tree.heading("name", text="Имя устройства")
        self.devices_tree.heading("token", text="Токен")
        self.devices_tree.heading("active", text="Активность")

        # Заполняем таблицу данными из базы данных
        self.load_devices_data()

        self.devices_tree.pack(expand=True, fill='both', padx=10, pady=10)

        # Кнопка для добавления новой записи
        add_button = ttk.Button(devices_window, text="Добавить устройство", command=self.add_device)
        add_button.pack(pady=5)

        # Кнопка для активации/деактивации устройства
        toggle_button = ttk.Button(devices_window, text="Активация/Деактивация", command=self.toggle_device)
        toggle_button.pack(pady=5)

        # Кнопка для закрытия окна
        close_button = ttk.Button(devices_window, text="Закрыть", command=devices_window.destroy)
        close_button.pack(pady=10)

        # Ожидаем закрытия модального окна
        self.root.wait_window(devices_window)

    def load_devices_data(self):
        """Загружает данные из таблицы Devices и заполняет таблицу."""
        # Очищаем текущие записи в Treeview
        self.devices_tree.delete(*self.devices_tree.get_children())

        devices = self.client_db.get_all_devices() 
        for device in devices:
            active_status = "Активно" if device['active'] == 1 else "НЕ активно"
            self.devices_tree.insert("", "end", values=(device['name'], device['token'], active_status))

    def add_device(self):
        """Добавляет новое устройство."""
        add_device_window = tk.Toplevel(self.root)  # Создаем новое окно
        add_device_window.title("Добавить устройство")
        add_device_window.geometry("300x200")

        # Устанавливаем окно как модальное
        add_device_window.transient(self.root)  # Устанавливаем родительское окно
        add_device_window.grab_set()  # Блокируем взаимодействие с родительским окном

        # Поля для ввода данных устройства
        tk.Label(add_device_window, text="Имя устройства:").pack(pady=5)
        name_entry = tk.Entry(add_device_window)
        name_entry.pack(pady=5)

        tk.Label(add_device_window, text="Токен:").pack(pady=5)
        token_entry = tk.Entry(add_device_window)
        token_entry.pack(pady=5)

        # Кнопка для сохранения нового устройства
        save_button = ttk.Button(add_device_window, text="Сохранить", command=lambda: self.save_new_device(name_entry.get(), token_entry.get(), add_device_window))
        save_button.pack(pady=10)

    def save_new_device(self, name, token, window):
        """Сохраняет новое устройство в базе данных."""
        if not name or not token:
            messagebox.showerror("Ошибка", "Имя устройства и токен не могут быть пустыми.")
            return

        # Сохраняем устройство в базе данных с активностью по умолчанию равной 1
        self.client_db.add_device(name, token, 1)

        messagebox.showinfo("Успех", "Устройство добавлено!")
        window.destroy()  # Закрываем окно добавления устройства
        self.load_devices_data()  # Обновляем таблицу устройств

    def toggle_device(self):
        """Активация/деактивация выбранного устройства."""
        selected_item = self.devices_tree.selection()
        if not selected_item:
            messagebox.showwarning("Предупреждение", "Пожалуйста, выберите устройство.")
            return

        device_name = self.devices_tree.item(selected_item)['values'][0]
        current_status = self.devices_tree.item(selected_item)['values'][2]

        # Логика для переключения статуса
        new_status = 0 if current_status == "Активно" else 1
        self.client_db.update_device_status(device_name, new_status)  # Обновляем статус в базе данных

        # Обновляем статус в Treeview
        new_status_text = "Активно" if new_status == 1 else "НЕ активно"
        self.devices_tree.item(selected_item, values=(device_name, self.devices_tree.item(selected_item)['values'][1], new_status_text))

    def open_send_km_dialog(self):
        """Создает модальное окно для отправки КМ."""
        send_km_window = tk.Toplevel(self.root)  # Создаем новое окно
        send_km_window.title("Отправить КМ")
        send_km_window.geometry("500x370")  # Увеличиваем высоту формы

        # Устанавливаем окно как модальное
        send_km_window.transient(self.root)
        send_km_window.grab_set()

        # Выбор товарной группы
        tk.Label(send_km_window, text="Выберите товарную группу:").pack(pady=5)
        selected_product_group = tk.StringVar()
        product_group_dropdown = ttk.Combobox(send_km_window, textvariable=selected_product_group, width=40)  # Увеличиваем ширину
        product_group_dropdown['values'] = self.client_db.get_all_tmp_product_group_names()  # Получаем товарные группы
        product_group_dropdown.pack(pady=10)

        # Выбор типа использования
        tk.Label(send_km_window, text="Выберите тип использования:").pack(pady=5)
        selected_type_of_use = tk.StringVar()
        type_of_use_dropdown = ttk.Combobox(send_km_window, textvariable=selected_type_of_use, width=40)  # Увеличиваем ширину
        type_of_use_dropdown['values'] = self.client_db.get_type_of_use_description()  # Получаем типы использования
        type_of_use_dropdown.pack(pady=10)

        # Выбор устройства
        tk.Label(send_km_window, text="Выберите устройство:").pack(pady=5)
        selected_activ_device = tk.StringVar()
        activ_device_dropdown = ttk.Combobox(send_km_window, textvariable=selected_activ_device, width=40)  # Увеличиваем ширину
        activ_device_dropdown['values'] = [device['name'] for device in self.client_db.get_active_devices()]  # Получаем активные устройства
        activ_device_dropdown.pack(pady=10)

        # Выбор JSON файла
        tk.Label(send_km_window, text="Выберите JSON файл:").pack(pady=5)
        json_file_path = tk.StringVar()
        json_file_entry = tk.Entry(send_km_window, textvariable=json_file_path)
        json_file_entry.pack(pady=5)
        json_file_button = ttk.Button(send_km_window, text="Обзор", command=lambda: self.select_json_file(json_file_path))
        json_file_button.pack(pady=5)

        # Кнопка для отправки данных
        send_button = ttk.Button(send_km_window, text="Отправить", command=lambda: self.send_km_data(
            selected_product_group.get(),
            selected_type_of_use.get(),
            json_file_path.get(),
            selected_activ_device.get()

        ))
        send_button.pack(pady=10)

        # Ожидаем закрытия окна
        self.root.wait_window(send_km_window)

    def select_json_file(self, json_file_path):
        """Открывает диалог для выбора JSON файла."""
        file_path = filedialog.askopenfilename(
            title="Выберите JSON файл",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            json_file_path.set(file_path)

    def send_km_data(self, product_group, type_of_use, json_file, token):
        """Обрабатывает отправку данных КМ."""
        # Проверка входных данных
        if not product_group:
            messagebox.showerror("Ошибка", "Выберите товарную группу")
            return
            
        if not type_of_use:
            messagebox.showerror("Ошибка", "Выберите тип использования")
            return
            
        if not json_file:
            messagebox.showerror("Ошибка", "Выберите JSON файл с данными")
            return
            
        if not token:
            messagebox.showerror("Ошибка", "Выберите устройство")
            return
            
        # Список для хранения штрих-кодов и даты
        sntins = []
        date_manufacture = None
        date_expiration = None
        claim_number = None
        name_product = None

        def extract_data(data):
            """Рекурсивная функция для извлечения штрих-кодов и дат."""
            nonlocal date_manufacture, date_expiration, claim_number, name_product
            if isinstance(data, dict):
                # Извлечение даты производства и даты истечения срока
                if 'DateManufacture' in data:
                    date_manufacture = data['DateManufacture']
                if 'DateExpiration' in data:
                    date_expiration = data['DateExpiration']
                if 'ClaimNumber' in data:
                    claim_number = data['ClaimNumber']
                if 'NameProduct' in data:
                    name_product = data['NameProduct']
                # Проверяем, есть ли ключ 'Barcode' и 'level'
                if 'Barcode' in data and data.get('level') == 0:
                    sntins.append(data['Barcode'])
                # Рекурсивно обходим все ключи в словаре
                for key, value in data.items():
                    extract_data(value)
            elif isinstance(data, list):
                # Рекурсивно обходим все элементы списка
                for item in data:
                    extract_data(item)

        # Чтение JSON файла
        try:
            logger.info(f"Начата отправка КМ. Товарная группа: {product_group}, Тип использования: {type_of_use}")
            
            with open(json_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                # Запускаем рекурсивную функцию
                extract_data(data)
                
            # Валидация извлеченных данных
            if not sntins:
                logger.error("Не найдены штрих-коды в файле JSON")
                raise Exception("Не найдены штрих-коды (sntins) в файле JSON")
                
            if not date_manufacture:
                logger.error("Не найдена дата производства в файле JSON")
                raise Exception("Не найдена дата производства (DateManufacture) в файле JSON")
                
            if not date_expiration:
                logger.error("Не найдена дата истечения срока в файле JSON")
                raise Exception("Не найдена дата истечения срока (DateExpiration) в файле JSON")
                
            if not claim_number:
                logger.error("Не найден номер заявки в файле JSON")
                raise Exception("Не найден номер заявки (ClaimNumber) в файле JSON")
                
            if not name_product:
                logger.error("Не найдено название продукта в файле JSON")
                raise Exception("Не найдено название продукта (NameProduct) в файле JSON")
                
            # Проверка формата дат
            try:
                datetime.strptime(date_manufacture, "%Y.%m.%d")
                datetime.strptime(date_expiration, "%Y.%m.%d")
            except ValueError:
                logger.error("Неверный формат даты в файле JSON")
                raise Exception("Неверный формат даты. Требуемый формат: ГГГГ.ММ.ДД")

            extension = self.client_db.get_product_group_code_by_name(product_group)
            device_token = self.client_db.get_device_token(token)
            
            if not extension:
                logger.error(f"Не найден код для товарной группы: {product_group}")
                raise Exception(f"Не удалось получить код товарной группы: {product_group}")
                
            if not device_token:
                logger.error(f"Не найден токен для устройства: {token}")
                raise Exception(f"Не удалось получить токен устройства: {token}")
                
            usage_type = self.client_db.get_type_of_use_code_by_name(type_of_use)
            if not usage_type:
                logger.error(f"Не найден код для типа использования: {type_of_use}")
                raise Exception(f"Не удалось получить код типа использования: {type_of_use}")

            json_data = {
                "sntins": sntins,
                "usageType": usage_type,
                "brandcode": name_product,
                "productionDate": datetime.strptime(date_manufacture, "%Y.%m.%d").isoformat()+"Z",
                "expirationDate": datetime.strptime(date_expiration, "%Y.%m.%d").isoformat()+"Z",
                "seriesNumber": claim_number
            }
            
            logger.info(f"Отправка данных КМ. Количество штрих-кодов: {len(sntins)}")
            result = self.legacy_api_client.send_mark(json_data, extension, device_token)
            
            if result == 200:
                logger.info("Данные КМ успешно отправлены")
                messagebox.showinfo("Успех", "Данные успешно отправлены!")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка при чтении JSON файла: {str(e)}")
            messagebox.showerror("Ошибка", "Ошибка при загрузке JSON файла, проверьте формат или путь.")
        except Exception as e:
            logger.error(f"Ошибка отправки данных КМ: {str(e)}", exc_info=True)
            messagebox.showerror("Ошибка", f"Ошибка отправки данных: {str(e)}")


if __name__ == "__main__":
    app = Main()
    app.run()