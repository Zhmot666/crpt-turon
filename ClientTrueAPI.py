from tkinter import messagebox

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
            return None
        except requests.exceptions.HTTPError as e:
            return e

    def auth_get(self):
        # Получение UUID и data для подписи
        auth_data = self.make_request('GET', '/auth/key')
        self.uuid = auth_data['uuid']
        return auth_data['data']

    def auth_post(self, signed_data):
        # Отправка подписанных данных для получения токена
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
        try:
            balance_data = self.get_balance_info()
            if balance_data is None:
                raise Exception("Не удалось получить данные о балансе")

            return balance_data  # Возвращаем данные о балансе

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при обновлении баланса: {str(e)}")
            return None  # Возвращаем None в случае ошибки
