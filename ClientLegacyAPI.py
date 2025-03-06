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
        
        try:
            # Устанавливаем таймаут для операции
            response = requests.post(url, headers=headers, json=data, timeout=30, verify=False)
            
            # Проверяем HTTP-статус ответа
            if response.status_code == 200:
                return 200  # Возвращаем код успеха для единообразия
            # Ответ сервера не 200, но в JSON-формате
            elif response.headers.get('Content-Type', '').startswith('application/json'):
                error_data = response.json()
                error_message = error_data.get("message", "Неизвестная ошибка сервера")
                
                if "globalErrors" in error_data:
                    error_details = error_data.get("globalErrors", [])[0].get("error", "")
                    error_message = f"{error_message}: {error_details}"
                
                raise Exception(error_message)
            # Ответ сервера не в JSON-формате
            else:
                raise Exception(f"Сервер вернул код {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            raise Exception("Превышено время ожидания ответа от сервера")
            
        except requests.exceptions.ConnectionError:
            raise Exception("Не удалось установить соединение с сервером")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка при отправке запроса: {str(e)}")
            
        except Exception as e:
            # Пробрасываем исключение дальше
            raise
