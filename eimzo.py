import asyncio
import websockets
import json
import ssl

async def get_certificates():
    uri = "wss://127.0.0.1:64443/service/cryptapi"
    
    # Создаем SSL контекст, который игнорирует проверку сертификата
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    headers = {
        "Host": "127.0.0.1:64443",
        "Origin": "https://127.0.0.1"  # Замените на ваш сайт
    }

    async with websockets.connect(uri, ssl=ssl_context, extra_headers=headers) as websocket:
        request = {
            "plugin": "pfx",
            "name": "list_all_certificates"
        }
        
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        
        return json.loads(response)

def print_certificates(data):
    if data.get("success"):
        print("Доступные сертификаты:")
        for cert in data.get("certificates", []):
            print("--------------------")
            print(f"Диск: {cert['disk']}")
            print(f"Путь: {cert['path']}")
            print(f"Имя: {cert['name']}")
            # print(f"Алиас: {cert['alias']}")
            print("--------------------")
            list_certificates = cert['alias'].split(',')
            for certificate in list_certificates:
                print(certificate)
            print("--------------------")

    else:
        print("Не удалось получить список сертификатов")

# Запуск асинхронной функции
async def main():
    try:
        certificates_data = await get_certificates()
        print_certificates(certificates_data)
    except Exception as e:
        print(f"Произошла ошибка: {e}")

# Запуск главной функции
if __name__ == "__main__":
    asyncio.run(main())