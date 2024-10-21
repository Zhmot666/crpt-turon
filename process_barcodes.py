import json
import csv
import os

def process_json(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)
    
    for task_mark in data.get('TaskMarks', []):
        for barcode_group in task_mark.get('Barcodes', []):
            process_barcode_group(barcode_group)

def process_barcode_group(group):
    if group.get('level') == 1:
        filename = f"{group['Barcode']}.csv"
        child_barcodes = [child['Barcode'].split('\u001d')[0] for child in group.get('ChildBarcodes', []) if child.get('level') == 0]
        
        if child_barcodes:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # writer.writerow(['Barcode'])  # Header
                for barcode in child_barcodes:
                    writer.writerow([barcode])
            print(f"Created file: {filename}")
    
    for child in group.get('ChildBarcodes', []):
        if isinstance(child, dict) and 'ChildBarcodes' in child:
            process_barcode_group(child)

# Путь к вашему JSON файлу
json_file_path = 'code.json'

# Обработка файла
process_json(json_file_path)