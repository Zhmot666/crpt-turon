import json
import tkinter as tk
from tkinter import filedialog, simpledialog

def remove_barcode_and_children(data, barcode_to_remove):
    """Рекурсивно удаляет блок данных с указанным Barcode и его дочерние элементы из структуры данных."""
    if isinstance(data, dict):
        # Если это словарь, проверяем все ключи
        if data.get('Barcode') == barcode_to_remove:
            print(f"Удаляем Barcode: {data.get('Barcode')}")
            return True  # Удаляем этот элемент
        # Рекурсивно проверяем все значения в словаре
        for key in list(data.keys()):  # Используем list() для безопасного удаления
            if remove_barcode_and_children(data[key], barcode_to_remove):
                del data[key]  # Удаляем элемент из родителя
        return False  # Если ничего не было удалено
    elif isinstance(data, list):
        # Если это список, проверяем каждый элемент
        for item in data[:]:  # Используем срез, чтобы избежать изменения списка во время итерации
            if remove_barcode_and_children(item, barcode_to_remove):
                data.remove(item)  # Удаляем элемент из списка
    return False  # Если ничего не было удалено

def select_file_and_barcode():
    """Выбор файла и Barcode для удаления."""
    # Создаем главное окно
    root = tk.Tk()
    root.withdraw()  # Скрываем главное окно

    # Открываем диалог для выбора файла
    json_file_path = filedialog.askopenfilename(title="Выберите JSON файл", filetypes=[("JSON files", "*.json")])
    if not json_file_path:
        print("Файл не выбран.")
        return

    # Запрашиваем Barcode для удаления
    barcode_to_remove = simpledialog.askstring("Удаление Barcode", "Введите Barcode для удаления:")
    if not barcode_to_remove:
        print("Barcode не введен.")
        return

    # Считываем данные из JSON файла
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Удаляем указанный Barcode и его дочерние элементы
    remove_barcode_and_children(data, barcode_to_remove)

    # Сохраняем изменения обратно в файл
    with open(json_file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    print(f"Barcode {barcode_to_remove} успешно удален.")

    # Проверка, остался ли Barcode в файле
    with open(json_file_path, 'r', encoding='utf-8') as file:
        updated_data = json.load(file)
        remaining_barcodes = [bg.get('Barcode') for task_mark in updated_data.get('TaskMarks', []) for bg in task_mark.get('Barcodes', [])]
        if barcode_to_remove in remaining_barcodes:
            print(f"Ошибка: Barcode {barcode_to_remove} все еще присутствует в файле.")
        else:
            print(f"Barcode {barcode_to_remove} успешно удален из файла.")

# Запуск функции выбора файла и Barcode
select_file_and_barcode()
