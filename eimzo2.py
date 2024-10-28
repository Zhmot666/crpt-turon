import tkinter as tk
from tkinter import ttk, scrolledtext
import websocket
import json
import ssl
import re
import base64


class CertificateSelector:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Подписание документа ЭЦП")
        self.root.geometry("800x600")

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

        # Фрейм для ввода текста
        input_frame = ttk.LabelFrame(self.root, text="Текст для подписи", padding=10)
        input_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Поле ввода текста
        self.input_text = scrolledtext.ScrolledText(
            input_frame, 
            wrap=tk.WORD, 
            height=8
        )
        self.input_text.pack(fill="both", expand=True)

        # Кнопка подписания
        self.sign_button = ttk.Button(
            self.root, 
            text="Подписать", 
            command=self.sign_text
        )
        self.sign_button.pack(pady=10)

        # Фрейм для вывода результата
        output_frame = ttk.LabelFrame(self.root, text="Результат подписи", padding=10)
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Поле вывода результата
        self.output_text = scrolledtext.ScrolledText(
            output_frame, 
            wrap=tk.WORD, 
            height=8
        )
        self.output_text.pack(fill="both", expand=True)

        # Загружаем сертификаты
        self.certificates = self.load_certificates()
        if self.certificates:
            self.fill_combobox()

    def extract_cn(self, alias):
        """Извлекает значение CN из строки алиаса"""
        cn_match = re.search(r'cn=(.*?),', alias)
        return cn_match.group(1) if cn_match else "Неизвестно"

    def load_certificates(self):
        """Загружает список сертификатов через WebSocket"""
        try:
            ws = websocket.create_connection(
                "wss://127.0.0.1:64443/service/cryptapi",
                sslopt={"cert_reqs": ssl.CERT_NONE}
            )
            
            request = {
                "plugin": "pfx",
                "name": "list_all_certificates"
            }
            
            ws.send(json.dumps(request))
            response = ws.recv()
            ws.close()
            
            data = json.loads(response)
            if data.get("success"):
                return data.get("certificates", [])
            else:
                print("Ошибка получения сертификатов")
                return None
                
        except Exception as e:
            print(f"Ошибка подключения к E-IMZO: {e}")
            return None

    def fill_combobox(self):
        """Заполняет комбобокс данными сертификатов"""
        self.cert_list = []  # Сохраняем полные данные сертификатов
        combo_items = []
        for cert in self.certificates:
            name = cert['name']
            cn = self.extract_cn(cert['alias'])
            self.cert_list.append(cert)  # Сохраняем полные данные
            combo_items.append(f"{name} - {cn}")
        
        self.combo['values'] = combo_items
        if combo_items:
            self.combo.set(combo_items[0])

    def sign_text(self):
        """Подписывает введенный текст"""
        if not self.cert_var.get():
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, "Ошибка: Не выбран сертификат")
            return

        text_to_sign = self.input_text.get(1.0, tk.END).strip()
        if not text_to_sign:
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, "Ошибка: Нет текста для подписи")
            return

        try:
            selected_index = self.combo.current()
            cert_data = self.cert_list[selected_index]
            
            # 1. Сначала загружаем ключ
            ws = websocket.create_connection(
                "wss://127.0.0.1:64443/service/cryptapi",
                sslopt={"cert_reqs": ssl.CERT_NONE}
            )

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
            
            print("Загрузка ключа:", json.dumps(load_key_request, indent=2))
            ws.send(json.dumps(load_key_request))
            key_response = ws.recv()
            print("Ответ на загрузку ключа:", key_response)
            key_response = json.loads(key_response)
            
            if not key_response.get("success"):
                raise Exception(f"Ошибка загрузки ключа: {key_response.get('reason', 'Неизвестная ошибка')}")
            
            key_id = key_response.get("keyId")
            if not key_id:
                raise Exception("Не удалось получить ID ключа")

            # 2. Кодируем текст в BASE64
            text_base64 = base64.b64encode(text_to_sign.encode()).decode()

            # 3. Создаем PKCS7 подпись
            sign_request = {
                "plugin": "pkcs7",
                "name": "create_pkcs7",
                "arguments": [
                    text_base64,    # данные в BASE64
                    key_id,         # идентификатор ключа
                    'no'           # не отсоединенная подпись
                ]
            }

            print("Создание подписи:", json.dumps(sign_request, indent=2))
            ws.send(json.dumps(sign_request))
            sign_response = ws.recv()
            print("Ответ на создание подписи:", sign_response)
            sign_response = json.loads(sign_response)
            ws.close()

            if sign_response.get("success"):
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, sign_response.get("pkcs7_64", "Подпись создана, но не получены данные"))
            else:
                error_message = sign_response.get("reason", "Неизвестная ошибка")
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, f"Ошибка подписи: {error_message}")

        except Exception as e:
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, f"Ошибка: {str(e)}")
            if 'ws' in locals():
                ws.close()

    def run(self):
        """Запускает главный цикл приложения"""
        self.root.mainloop()

    def get_available_functions(self):
        """Получает список доступных функций"""
        try:
            ws = websocket.create_connection(
                "wss://127.0.0.1:64443/service/cryptapi",
                sslopt={"cert_reqs": ssl.CERT_NONE}
            )

            # Запрос списка доступных функций
            list_request = {
                "name": "list_all_functions"
            }

            print("Запрос списка функций:", json.dumps(list_request, indent=2))
            ws.send(json.dumps(list_request))
            response = ws.recv()
            print("Доступные функции:", response)
            ws.close()

            return json.loads(response)

        except Exception as e:
            print(f"Ошибка при получении списка функций: {str(e)}")
            return None


# Создание и запуск приложения
if __name__ == "__main__":
    app = CertificateSelector()
    app.run()
