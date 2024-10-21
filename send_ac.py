import requests
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

class TrueAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'cache-control': 'no-cache'
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
            """
            Функция для подписи данных с помощью ЭЦП.
            """
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

            # Вводим PIN-код (ВНИМАНИЕ: Это небезопасно!)
            PIN_CODE = "53753734"  # Замените на реальный PIN-код
            self.driver.switch_to.active_element.send_keys(PIN_CODE + Keys.ENTER)

            # Ждем, пока появится подписанный документ
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.NAME, "pkcs7"))
            )

            # Получаем подписанный документ
            pkcs7_textarea = self.driver.find_element(By.NAME, "pkcs7")
            signed_data = pkcs7_textarea.get_attribute('value')

            return signed_data

    def __del__(self):
        if self.driver:
            self.driver.quit()

# Пример использования
if __name__ == "__main__":
    api = TrueAPI('https://aslbelgisi.uz/api/v3/true-api')  # Замените на реальный URL API
    
    try:
        token = api.authenticate()
        print(f"Успешная аутентификация. Полученный токен: {token}")
    except Exception as e:
        print(f"Ошибка при аутентификации: {str(e)}")