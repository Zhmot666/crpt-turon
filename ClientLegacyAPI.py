import requests


class ClientLegacyAPI:
    def __init__(self, url, client_db):
        self.omsId = client_db.get_oms_id()  # Загружаем omsId из базы данных таблицы Setting
        self.url = url

    def check_connection(self, token, extension):
        try:
            url = f"{self.url}/{extension}/ping?omsId={self.omsId}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'clientToken': f'{token}'
            }
            response = requests.get(url, headers=headers, verify=False)

            if response.status_code == 200:
                data = response.json()
                return f"Подключение успешно: {data['omsId']}"
            else:
                return f"Ошибка: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Ошибка при проверке подключения: {str(e)}"

    def send_aggregation(self, data, extension, token):
        url = f"{self.url}/{extension}/aggregation?omsId={self.omsId}"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'clientToken': f'{token}'
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
