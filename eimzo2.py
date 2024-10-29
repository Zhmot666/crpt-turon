import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import websocket
import json
import ssl
import re
import base64
import requests

class ClientTrueAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.headers = {}

    def get_balance_info(self):
        url = self.base_url + "/elk/product-groups/balance/all"
        response = requests.get(url, headers=self.current_token)
        
        if response.status_code == 200:
            balances = response.json()
            return balances
        else:
            # Заменяем вывод в консоль на модальное окно
            messagebox.showerror("Ошибка", f"Ошибка при получении баланса. Код ошибки: {response.status_code}\nСообщение об ошибке: {response.text}")
            return None


    def update_balance(self):
        """Обновляет информацию о балансе"""
        try:
            balance_data = self.get_balance_info()
            print("Данные о балансе:", balance_data)

            if balance_data is None:
                raise Exception("Не удалось получить данные о балансе")

            self.balance_labels['balance'].config(text=f"Баланс: {balance_data['balance']}")
            self.balance_labels['reserved'].config(text=f"Зарезервировано: {balance_data['reserved']}")
            self.balance_labels['available'].config(text=f"Доступно: {balance_data['available']}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при обновлении баланса: {str(e)}")


class ClientCryptAPI:
    def __init__(self, base_url):
        self.base_url = base_url

    def load_certificates(self):
        """Загружает список сертификатов"""
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
                self.cert_list = certificates.get("certificates", [])
                self.fill_combobox()
            else:
                messagebox.showerror("Ошибка", "Не удалось загрузить сертификаты")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке сертификатов: {str(e)}")
            

class CertificateSelector:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Подключение к ЭЦП")
        self.root.geometry("800x400")
        
        # Инициализация API-клиентов
        self.true_api_client = ClientTrueAPI("https://aslbelgisi.uz/api/v3/true-api/auth/key")
        self.crypt_api_client = ClientCryptAPI("http://127.0.0.1:64443/service/cryptapi")

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
            command=self.connect_certificate
        )
        self.connect_button.pack(pady=10)

        # рейм для отображения баланса
        balance_frame = ttk.LabelFrame(self.root, text="Информация о балансе", padding=10)
        balance_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Метки для отображеня информации о балансе
        self.balance_labels = {
            'balance': ttk.Label(balance_frame, text="Баланс: "),
            'reserved': ttk.Label(balance_frame, text="Зарезервировано: "),
            'available': ttk.Label(balance_frame, text="Доступно: ")
        }
        for label in self.balance_labels.values():
            label.pack(anchor='w', pady=2)

        # Загружаем сертификаты
        self.cert_list = []
        self.load_certificates()

        # Добавляем переменные для хранения текущего состояния
        self.current_key_id = None
        self.current_cert_data = None
        self.current_token = None

        # Кнопка для обновления баланса
        self.update_balance_button = ttk.Button(
            self.root,
            text="Обновить баланс",
            command=self.update_balance  # Привязываем метод к кнопке
        )
        self.update_balance_button.pack(pady=10)



    def fill_combobox(self):
        """Заполняет комбобокс данными сертификатов"""
        cert_list = []
        for cert in self.cert_list:
            alias = cert.get('alias', '').upper()
            # Зменяем идентификаторы на более читаемые
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
        """Обработчик нажатия кнопки Подключиться"""
        if not self.cert_var.get():
            messagebox.showerror("Ошибка", "Не выбран сертификат")
            return

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


    def run(self):
        """Запускает главный цикл приложения"""
        self.root.mainloop()

# Создание и запуск приложения
if __name__ == "__main__":
    app = CertificateSelector()
    app.run()
