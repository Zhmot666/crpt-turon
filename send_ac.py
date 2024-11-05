import requests
import time
# import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.keys import Keys


class TrueAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
        self.driver = webdriver.Chrome()  # Убедитесь, что у вас установлен ChromeDriver

    def make_request(self, method, endpoint, data=None):
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Content: {response.text}")
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.JSONDecodeError:
            print("Не удалось декодировать JSON")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"HTTP ошибка: {e}")
            return None
    
    def authenticate(self):
        """
        Процесс аутентификации с использованием ЭЦП.
        """
        # Шаг 1: Получение UUID и data для подписи
        auth_data = self.make_request('GET', '/auth/key')
        uuid = auth_data['uuid']
        data_to_sign = auth_data['data']

        # Шаг 2: Подписание данных с помощью ЭЦП
        signed_data = self.sign_data(data_to_sign)

        # Шаг 3: Отправка подписанных данных для получения токена
        auth_response = self.make_request('POST', '/auth/simpleSignIn', {
            'uuid': uuid,
            'data': signed_data
        })

        if 'token' in auth_response:
            self.token = auth_response['token']
            self.headers['Authorization'] = f'Bearer {self.token}'
            return self.token
        else:
            raise Exception("Ошибка аутентификации: токен не получен")

    def sign_data(self, data_to_sign):
        # Функция для подписи данных с помощью ЭЦП.

        # Загружаем страницу для подписи
        self.driver.get('http://dls.yt.uz/certkey-pfx-token-pkcs7.html')

        # Ждем, пока загрузится список ключей
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "key"))
        )

        # Вставляем данные для подписи
        data_textarea = self.driver.find_element(By.NAME, "data")
        data_textarea.clear()
        data_textarea.send_keys(data_to_sign)

        # Нажимаем кнопку "Подписать"
        sign_button = self.driver.find_element(By.XPATH, "//button[text()='Подписать']")
        sign_button.click()

        # Ждем появления диалога для ввода PIN-кода
        time.sleep(30)  # Даем время для появления диалога

        # Ждем, пока появится подписанный документ
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.NAME, "pkcs7"))
        )

        # Получаем подписанный документ
        pkcs7_textarea = self.driver.find_element(By.NAME, "pkcs7")
        signed_data = pkcs7_textarea.get_attribute('value')

        return signed_data

    def get_balance(self):
        """
        Получение баланса УОТ по всем ТГ.
        """
        url = f"{self.base_url}/elk/product-groups/balance/all"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            balances = response.json()
            return balances
        else:
            print(f"Ошибка при получении баланса. Код ошибки: {response.status_code}")
            print(f"Сообщение об ошибке: {response.text}")
            return None

    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

    @staticmethod
    def ping(extension, oms_id, client_token):
        import requests

        url = f"https://aslbelgisi.uz/api/v3/{extension}/ping?omsId={oms_id}"
        headers = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }
        print('Старт')
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Проверка на успешный ответ

            data = response.json()
            return {
                'omsId': data.get('omsId'),
                'success': data.get('success')
            }
        except requests.exceptions.HTTPError as http_err:
            error_data = response.json() if response.content else {}
            return {
                'success': False,
                'globalErrors': error_data.get('globalErrors', []),
                'omsId': error_data.get('omsId', None)
            }
        except Exception as err:
            return {
                'success': False,
                'globalErrors': [{'error': str(err), 'errorCode': 0}]
            }


def get_name_product_group(product_group_id):
    match product_group_id:
        case 3:
            return "Табачная продукция"
        case 7:
            return "Лекарственные средства"
        case 11:
            return "Алкогольная продукция"
        case 13:
            return "Вода и прохладительные напитки"
        case 15:
            return "Пиво и пивные напитки"
        case 18:
            return "Бытовая техника"
        case 19:
            return "Спиртосодержащая непищевая продукция"


def print_balance(balances):
    """
    Вывод информации о балансе в консоль.
    """
    if not balances:
        print("Нет данных о балансе.")
        return

    print("Баланс по товарным группам:")
    for balance in balances:
        org_id = balance.get('organisationId', 'Не указан')
        product_group_id = get_name_product_group(balance.get('productGroupId', 'Не указан'))
        balance_amount = balance.get('balance', 'Не указан')
        contract_id = balance.get('contractId', 'Не указан')

        print("--------------------")
        print(f"Организация ID: {org_id}")
        print(f"Товарная группа ID: {product_group_id}")
        if balance_amount != 'Не указан':
            balance_str = f"{balance_amount // 100} сум {balance_amount % 100} тийин"
        else:
            balance_str = 'Не указан'
        print(f"Баланс: {balance_str}")
        print(f"Контракт ID: {contract_id}")
        print("--------------------")


def main():
    api = TrueAPI('https://aslbelgisi.uz/api/v3/true-api')
    
    
    try:
        token = api.authenticate()
        print(f"Успешная аутентификация. Полученный токен: {token}")
        balances = api.get_balance()
        print_balance(balances)
    except Exception as e:
        print(f"Ошибка при аутентификации: {str(e)}")
    
    print(TrueAPI.ping('pharma', '14113', token))


if __name__ == "__main__":
    main()
