import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import websocket
import json
import ssl
import re
import base64
import requests


class ClientTrueAPI:
    def __init__(self, base_url):
        self.balance_labels = None
        self.uuid = None
        self.base_url = base_url
        self.token = None
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }

    def make_request(self, method, endpoint, data=None):
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data)
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.JSONDecodeError:
            print("Не удалось декодировать JSON")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"HTTP ошибка: {e}")
            return None

    def auth_get(self):
        # Шаг 1: Получение UUID и data для подписи
        auth_data = self.make_request('GET', '/auth/key')
        self.uuid = auth_data['uuid']
        return auth_data['data']

    def auth_post(self, signed_data):
        # Шаг 3: Отправка подписанных данных для получения токена
        auth_response = self.make_request('POST', '/auth/simpleSignIn', {
            'uuid': self.uuid,
            'data': signed_data
        })

        if 'token' in auth_response:
            self.token = auth_response['token']
            self.headers['Authorization'] = f'Bearer {self.token}'
            return self.token
        else:
            raise Exception("Ошибка аутентификации: токен не получен")

    def get_balance_info(self):
        url = self.base_url + "/elk/product-groups/balance/all"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            balances = response.json()
            return balances
        else:
            messagebox.showerror("Ошибка", f"Ошибка при получении баланса. Код ошибки: "
                                           f"{response.status_code}\nСообщение о ошибке: {response.text}")
            return None

    def update_balance(self):
        """Обновляет информацию о балансе"""
        try:
            balance_data = self.get_balance_info()  # Убедитесь, что эта строка возвращает данные
            if balance_data is None:
                raise Exception("Не удалось получить данные о балансе")

            # Обновите метки на форме с использованием данных о балансе
            # self.balance_labels['balance'].config(text=f"Баланс: {balance_data['balance']}")
            return balance_data  # Возвращаем данные о балансе

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при обновлении баланса: {str(e)}")
            return None  # Возвращаем None в случае ошибки


class ClientCryptAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.cert_list = []
        self.selected_cert_index = None

    def set_selected_cert_index(self, index):
        self.selected_cert_index = index

    def load_certificates(self):
        """Загружает список сертификатов"""
        result = ''
        try:
            ws = websocket.create_connection(self.base_url, sslopt={"cert_reqs": ssl.CERT_NONE})
            
            list_certificates_request = {
                "plugin": "pfx",
                "name": "list_all_certificates"
            }
            
            ws.send(json.dumps(list_certificates_request))
            certificates = json.loads(ws.recv())
            ws.close()

            if certificates.get("success", False):
                result = certificates.get("certificates", [])
                # self.cert_list = certificates.get("certificates", [])
                # self.fill_combobox()
            else:
                messagebox.showerror("Ошибка", "Не удалось загрузить сертификаты")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке сертификатов: {str(e)}")

        return result

    def sign_data(self, data_to_sign, cert_list):
        if self.selected_cert_index is None:
            raise Exception("Сертификат не выбран")
        # cert_data = self.cert_list[self.selected_cert_index]
        cert_data = cert_list[self.selected_cert_index]

        ws = websocket.create_connection(
            "wss://127.0.0.1:64443/service/cryptapi",
            sslopt={"cert_reqs": ssl.CERT_NONE}
        )

        # Загружаем ключ
        load_key_request = {
            "plugin": "pfx",
            "name": "load_key",
            "arguments": [
                cert_data['disk'],
                cert_data['path'],
                cert_data['name'],
                cert_data.get('alias', '')
            ]
        }

        ws.send(json.dumps(load_key_request))
        key_response = json.loads(ws.recv())

        if not key_response.get("success"):
            raise Exception(f"Ошибка загрузки ключа: {key_response.get('reason', 'Неизвестная ошибка')}")

        key_id = key_response.get("keyId")

        # Создаем подпись
        sign_request = {
            "plugin": "pkcs7",
            "name": "create_pkcs7",
            "arguments": [
                base64.b64encode(data_to_sign.encode()).decode(),
                key_id,
                'no'
            ]
        }

        ws.send(json.dumps(sign_request))
        sign_response = json.loads(ws.recv())
        ws.close()

        if not sign_response.get("success"):
            raise Exception(f"Ошибка создания подписи: {sign_response.get('reason', 'Неизвестная ошибка')}")

        signature = sign_response.get("pkcs7_64")
        return signature


class ClientLegacyAPI:
    def __init__(self, url):
        self.token = self.load_token()  # Считываем токен из файла token.txt
        self.omsId = self.load_oms_id()  # Считываем omsId из файла oms_id.txt
        self.url = url

    def load_token(self):
        """Загружает токен из файла token.txt"""
        try:
            with open('token.txt', 'r') as file:
                token = file.read().strip()  # Читаем токен и убираем лишние пробелы
                return token
        except FileNotFoundError:
            print("Файл token.txt не найден.")
            return None  # Возвращаем None, если файл не найден
        except Exception as e:
            print(f"Ошибка при чтении токена: {str(e)}")
            return None  # Возвращаем None в случае других ошибок

    def load_oms_id(self):
        """Загружает omsId из файла oms_id.txt"""
        try:
            with open('oms_id.txt', 'r') as file:
                oms_id = file.read().strip()  # Читаем omsId и убираем лишние пробелы
                return oms_id
        except FileNotFoundError:
            print("Файл oms_id.txt не найден.")
            return None  # Возвращаем None, если файл не найден
        except Exception as e:
            print(f"Ошибка при чтении omsId: {str(e)}")
            return None  # Возвращаем None в случае других ошибок

    def check_connection(self, extension):
        print(self.token)
        try:
            url = f"{self.url}/{extension}/ping?omsId={self.omsId}"
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'clientToken': f'{self.token}'
            }
            response = requests.get(url, headers=headers, verify=False)
            print(response)

            if response.status_code == 200:
                data = response.json()
                return f"Подключение успешно: {data['omsId']}"
            else:
                return f"Ошибка: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Ошибка при проверке подключения: {str(e)}"

    def send_aggregation(self, data, extension):
        url = f"{self.url}/{extension}/aggregation?omsId={self.omsId}"

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'clientToken': f'{self.token}'
        }

        try:
            response = requests.post(url, headers=headers, json=data, verify=False)

            if response.status_code == 200:
                result = response.json()
                return result  # Возвращаем результат для дальнейшей обработки
            else:
                error_info = response.json()
                error_message = error_info.get("globalErrors", [{"error": "Неизвестная ошибка"}])[0]["error"]
                raise Exception(f"Ошибка: {error_message}")

        except Exception as e:
            raise Exception(f"Ошибка при отправке агрегации: {str(e)}")


class Main:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Подключение к ЭЦП")
        self.root.geometry("800x400")
        
        # Индикатор подключения
        self.connection_status_label = ttk.Label(self.root, text="Статус подключения: Не подключено", foreground="red")
        self.connection_status_label.pack(pady=10)

        # Инициализация API-клиентов
        # self.true_api_client = ClientTrueAPI("https://aslbelgisi.uz/api/v3/true-api")
        self.true_api_client = ClientTrueAPI("https://goods.aslbelgisi.uz/api/v3/true-api")
        self.crypt_api_client = ClientCryptAPI("wss://127.0.0.1:64443/service/cryptapi")
        self.legacy_api_client = ClientLegacyAPI("https://omscloud.aslbelgisi.uz/api/v2")
        
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
        else:
            print('что-то пошло не к')
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
        button_frame.pack(pady=10)

        # Кнопка проверки подключения
        self.check_connection_button = ttk.Button(
            button_frame,
            text="Проверить подключение",
            command=self.check_connection
        )
        self.check_connection_button.pack(side=tk.LEFT)

        # Кнопка "Отправить агрегацию"
        self.send_aggregation_button = ttk.Button(
            button_frame,
            text="Отправить агрегацию",
            command=self.send_aggregation
        )
        self.send_aggregation_button.pack(side=tk.LEFT)  # Размещаем справа от кнопки проверки

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

    def _get_x500_val(self, x500name, field):
        """Извлекает значение поля из строки X500Name"""
        field_match = re.search(f"{field}=([^,]+)", x500name)
        return field_match.group(1) if field_match else ""

    def connect_certificate(self):
        ws = None
        try:
            # 1. Получаем UUID и данные для подписи
            auth_url = "https://aslbelgisi.uz/api/v3/true-api/auth/key"
            response = requests.get(auth_url)
            if response.status_code != 200:
                raise Exception("Ошибка получения данных для подписи")
            
            auth_data = response.json()
            uuid = auth_data['uuid']
            data_to_sign = auth_data['data']
            
            # 2. Подписываем полученные данные
            selected_index = self.combo.current()
            cert_data = self.cert_list[selected_index]
            
            ws = websocket.create_connection(
                "wss://127.0.0.1:64443/service/cryptapi",
                sslopt={"cert_reqs": ssl.CERT_NONE}
            )

            # Загружаем ключ
            load_key_request = {
                "plugin": "pfx",
                "name": "load_key",
                "arguments": [
                    cert_data['disk'],
                    cert_data['path'],
                    cert_data['name'],
                    cert_data.get('alias', '')
                ]
            }
            
            ws.send(json.dumps(load_key_request))
            key_response = json.loads(ws.recv())
            
            if not key_response.get("success"):
                raise Exception(f"Ошибка загрузки ключа: {key_response.get('reason', 'Неизвестная ошибка')}")
            
            key_id = key_response.get("keyId")

            # Создаем подпись
            sign_request = {
                "plugin": "pkcs7",
                "name": "create_pkcs7",
                "arguments": [
                    base64.b64encode(data_to_sign.encode()).decode(),
                    key_id,
                    'no'
                ]
            }

            ws.send(json.dumps(sign_request))
            sign_response = json.loads(ws.recv())
            ws.close()

            if not sign_response.get("success"):
                raise Exception(f"Ошибка создания подписи: {sign_response.get('reason', 'Неизвестная ошибка')}")

            signature = sign_response.get("pkcs7_64")

            # 3. Отправляем UUID и подпись для получения токена
            auth_confirm_url = "https://aslbelgisi.uz/api/v3/true-api/auth/simpleSignIn"
            confirm_response = requests.post(auth_confirm_url, json={
                'uuid': uuid,
                'data': signature
            })

            if confirm_response.status_code != 200:
                raise Exception(f"Ошибка получения токена: {confirm_response.text}")

            token_data = confirm_response.json()
            if 'token' not in token_data:
                raise Exception("Токен не получен в ответе")

            self.current_token = token_data['token']
            self.current_cert_data = cert_data

            # Обновляем информацию о балансе
            # self.update_balance()

            messagebox.showinfo("Успех", "Успешно подключено")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при подключении: {str(e)}")
            if 'ws' in locals():
                ws.close()

    def on_connect(self):
        try:
            # Ваш код для подключения
            data_to_sign = self.true_api_client.auth_get()
            selected_index = self.combo.current()
            self.crypt_api_client.set_selected_cert_index(selected_index)
            signed_data = self.crypt_api_client.sign_data(data_to_sign, self.cert_list)
            self.true_api_client.auth_post(signed_data)

            self.connection_status_label.config(text="Статус подключения: Успешно подключено", foreground="green")
        except Exception as e:
            self.connection_status_label.config(text=f"Статус подключения: Ошибка - {str(e)}", foreground="red")

    def run(self):
        """Запускает главный цикл приложения"""
        self.root.mainloop()

    def update_balance(self):
        balance_data = self.true_api_client.get_balance_info()
        if balance_data:
            self.balance_labels['balance'].config(text=f"Баланс: {balance_data['balance']}")
            # Обновите другие метки аналогично

    def on_update_balance_button_click(self):
        """Обработчик нажатия кнопки обновления баланса"""
        balance_info = self.true_api_client.update_balance()  # Вызов метода обновления баланса
        if balance_info:
            # Обновляем метки на форме с использованием данных из balance_info
            self.write_balance_in_form(balance_info)

            print("Баланс обновлен:", balance_info)
        else:
            print("Не удалось обновить баланс.")

    product_group_names_en = {
        3: "tobacco",
        7: "pharma",
        11: "alcohol",
        13: "water",
        15: "beer",
        18: "appliances",
        19: "antiseptic"
    }

    product_group_names_ru = {
        3: "Табачная продукция",
        7: "Лекарственные средства",
        11: "Алкогольная продукция",
        13: "Вода и прохладительные напитки",
        15: "Пиво и пивные напитки",
        18: "Бытовая техника",
        19: "Спиртосодержащая непищевая продукция"
    }

    def write_balance_in_form(self, balance_info):
        total_balance = balance_info[0]['balance']
        sumy = total_balance // 100
        tiyn = total_balance % 100

        self.balance_labels['balance'].config(text=f"Баланс: {sumy} сумов {tiyn} тийинов")
        self.balance_labels['contractId'].config(text=f"Номер контракта: {balance_info[0]['contractId']}")
        self.balance_labels['organisationId'].config(text=f"Код организации: {balance_info[0]['organisationId']}")

        product_group_id = balance_info[0]['productGroupId']
        product_group_name = self.product_group_names_ru.get(product_group_id, "Неизвестная группа")
        self.balance_labels['productGroupId'].config(text=f"Группа продукции: {product_group_name}")

    def check_connection(self):
        extension = "pharma"        # Замените на ваше значение
        result = self.legacy_api_client.check_connection(extension)
        messagebox.showinfo("Результат проверки", result)

    def send_aggregation(self):
        production_order_id = tk.simpledialog.askstring("Идентификатор производственного заказа",
                                                        "Идентификатор производственного заказа:")
        aggregation_unit_capacity = tk.simpledialog.askstring("Вместимость агрегированной единицы",
                                                              "Введите Вместимость агрегированной единицы:")
        
        # Открываем диалог выбора файл
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

            extension = "pharma"
            result = self.legacy_api_client.send_aggregation(data, extension)
            report_id = result.get("reportId")
            messagebox.showinfo("Успех", f"Отчет успешно отправлен. ID отчета: {report_id}")
            # print(data)
            
        except json.JSONDecodeError:
            messagebox.showerror("Ошибка", "Ошибка при загрузке JSON файла, проверьте формат.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
 
    def load_participant_id(self, file_path):
        """Загружает participantId из файла participantId.txt."""
        try:
            with open(file_path, 'r') as file:
                participant_id = file.read().strip()  # Читаем participantId и убираем лишние пробелы
                return participant_id
        except FileNotFoundError:
            print("Файл participantId.txt не найден.")
            return None  # Возвращаем None, если файл не найден
        except Exception as e:
            print(f"Ошибка при чтении participantId: {str(e)}")
            return None  # Возвращаем None в случае других ошибок

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
        
        # Считываем participantId из файла
        participant_id = self.load_participant_id('part_id.txt')
        if participant_id is None:
            return None

        # Считываем данные из JSON файла
        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Извлекаем агрегированные единицы
        aggregation_units = self.extract_sntins_and_serial_numbers(data)

        # Формируем итоговые данные
        request_data = {
            "participantId": participant_id,
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


if __name__ == "__main__":
    app = Main()
    app.run()
