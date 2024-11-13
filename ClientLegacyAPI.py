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
        """Отчет об агрегации"""
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

    def send_mark(self, data, extension, token):
        """Отчет о нанесении"""
        url = f"{self.url}/{extension}/utilisation?omsId={self.omsId}"
        
        headers = {
            "Authorization": f'Bearer {token}',
            "Content-Type": "application/json",
            "clientToken": f'{token}'
        }
        
        # Перед отправкой данных
        print(f"Отправляемые данные: {data}")

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()  # Проверяем статус ответа
            return response.json()  # Возвращаем успешный ответ
        except requests.exceptions.HTTPError as http_err:
            # Обработка ошибок HTTP
            print(f"HTTP error occurred: {http_err}")  # Логируем ошибку
            # Вы можете добавить дополнительную логику, например, отправку уведомлений
        except requests.exceptions.ConnectionError as conn_err:
            # Обработка ошибок соединения
            print(f"Connection error occurred: {conn_err}")  # Логируем ошибку
        except requests.exceptions.Timeout as timeout_err:
            # Обработка ошибок таймаута
            print(f"Timeout error occurred: {timeout_err}")  # Логируем ошибку
        except requests.exceptions.RequestException as req_err:
            # Обработка всех других ошибок запросов
            print(f"An error occurred: {req_err}")  # Логируем ошибку
        except Exception as e:
            # Обработка любых других исключений
            print(f"An unexpected error occurred: {e}")  # Логируем ошибку
