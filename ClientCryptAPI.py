import base64
import json
import ssl
from tkinter import messagebox

import websocket


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
