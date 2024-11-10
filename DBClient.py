import sqlite3


class ClientDB:
    def __init__(self, db_file):
        """Инициализирует подключение к базе данных SQLite."""
        self.connection = self.create_connection(db_file)
        self.create_tables()

    @staticmethod
    def create_connection(db_file):
        """Создает подключение к базе данных SQLite."""
        return sqlite3.connect(db_file)

    def create_tables(self):
        """Создает таблицы, если они не существуют, и заполняет их данными."""
        self.create_setting_table()
        self.create_product_group_table()
        self.create_tmp_product_group_table()
        self.create_devices_table()

    def create_setting_table(self):
        """Создает таблицу Setting, если она не существует, и заполняет её данными."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS Setting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            PathCryptAPI TEXT,
            PathTrueAPI TEXT,
            PathLegacyAPI TEXT,
            omsId TEXT,
            INN INTEGER CHECK(length(INN) = 9)
        );
        """
        cursor = self.connection.cursor()
        cursor.execute(create_table_sql)

        # Проверка на наличие данных в таблице
        cursor.execute("SELECT COUNT(*) FROM Setting")
        count = cursor.fetchone()[0]

        # Если таблица пуста, вставляем данные
        if count == 0:
            insert_data_sql = """
            INSERT INTO Setting (PathCryptAPI, PathTrueAPI, PathLegacyAPI, omsId, INN)
            VALUES (?, ?, ?, ?, ?);
            """
            data = (
                "wss://127.0.0.1:64443/service/cryptapi",
                "https://goods.aslbelgisi.uz/api/v3/true-api",
                "https://omscloud.aslbelgisi.uz/api/v2",
                "",
                123456789
            )
            cursor.execute(insert_data_sql, data)
            self.connection.commit()

    def create_product_group_table(self):
        """Создает таблицу product_group, если она не существует, и заполняет её данными."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS product_group (
            id INTEGER PRIMARY KEY,
            code TEXT,
            name TEXT
        );
        """
        cursor = self.connection.cursor()
        cursor.execute(create_table_sql)

        # Проверка на наличие данных в таблице
        cursor.execute("SELECT COUNT(*) FROM product_group")
        count = cursor.fetchone()[0]

        # Если таблица пуста, вставляем данные
        if count == 0:
            insert_data_sql = """
            INSERT INTO product_group (id, code, name)
            VALUES (?, ?, ?);
            """
            data = [
                (3, "tobacco", "Табачная продукция"),
                (7, "pharma", "Лекарственные средства"),
                (11, "alcohol", "Алкогольная продукция"),
                (13, "water", "Вода и прохладительные напитки"),
                (15, "beer", "Пиво и пивные напитки"),
                (18, "appliances", "Бытовая техника"),
                (19, "antiseptic", "Спиртосодержащая непищевая продукция")
            ]
            cursor.executemany(insert_data_sql, data)
            self.connection.commit()

    def create_tmp_product_group_table(self):
        """Создает таблицу tmp_product_group, если она не существует."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS tmp_product_group (
            id INTEGER PRIMARY KEY,
            code TEXT,
            name TEXT
        );
        """
        cursor = self.connection.cursor()
        cursor.execute(create_table_sql)

        # Очищаем таблицу tmp_product_group
        cursor.execute("DELETE FROM tmp_product_group")
        self.connection.commit()

    def create_devices_table(self):
        """Создает таблицу devices, если она не существует."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            token TEXT NOT NULL,
            active INTEGER CHECK(active IN (0, 1))
        );
        """
        cursor = self.connection.cursor()
        cursor.execute(create_table_sql)
        self.connection.commit()

    def get_setting_by_field(self, field_name):
        """Извлекает значение указанного поля из таблицы Setting."""
        cursor = self.connection.cursor()
        query = f"SELECT {field_name} FROM Setting"
        cursor.execute(query)
        return cursor.fetchall()

    def get_tmp_product_group_codes(self):
        """Извлекает все коды из таблицы tmp_product_group."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT code FROM tmp_product_group")
        return [row[0] for row in cursor.fetchall()]

    def close_connection(self):
        """Закрывает подключение к базе данных."""
        if self.connection:
            self.connection.close()

    def get_product_group_data(self):
        """Извлекает все записи из таблицы product_group."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM product_group")
        return cursor.fetchall()

    def clear_tmp_product_group(self):
        """Очищает таблицу tmp_product_group."""
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM tmp_product_group")
        self.connection.commit()

    def insert_into_tmp_product_group(self, group):
        """Вставляет запись в таблицу tmp_product_group."""
        cursor = self.connection.cursor()
        insert_sql = "INSERT INTO tmp_product_group (id, code, name) VALUES (?, ?, ?)"
        cursor.execute(insert_sql, group)  # group должен быть кортежем (id, code, name)
        self.connection.commit()

    def get_product_group_name(self, product_group_id):
        """Возвращает имя группы продуктов по ее идентификатору."""
        query = "SELECT name FROM product_group WHERE id = ?"
        cursor = self.connection.cursor()
        cursor.execute(query, (product_group_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_product_group_code_by_name(self, group_name):
        """Возвращает код группы продуктов по ее имени."""
        query = "SELECT code FROM product_group WHERE name = ?"
        cursor = self.connection.cursor()
        cursor.execute(query, (group_name,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_tmp_product_group_name(self, group_code):
        """Возвращает имя временной группы продуктов по ее коду."""
        query = "SELECT name FROM tmp_product_group WHERE code = ?"
        cursor = self.connection.cursor()
        cursor.execute(query, (group_code,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_all_tmp_product_group_names(self):
        """Возвращает имена всех временных групп продуктов из таблицы tmp_product_group."""
        query = "SELECT name FROM tmp_product_group"
        cursor = self.connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        return [row[0] for row in results]  # Возвращаем список имен

    def get_inn(self):
        """Возвращает значение INN из таблицы Setting."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT INN FROM Setting")
        result = cursor.fetchone()
        return result[0] if result else None

    def get_oms_id(self):
        """Возвращает значение omsId из таблицы Setting."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT omsId FROM Setting")
        result = cursor.fetchone()
        return result[0] if result else None

    def update_setting(self, settings):
        """Обновляет настройки в таблице Setting."""
        update_sql = """
        UPDATE Setting
        SET PathCryptAPI = ?, PathTrueAPI = ?, PathLegacyAPI = ?, omsId = ?, INN = ?
        WHERE id = 1;  -- Предполагается, что у вас только одна запись в таблице
        """
        cursor = self.connection.cursor()
        cursor.execute(update_sql, (
            settings['PathCryptAPI'],
            settings['PathTrueAPI'],
            settings['PathLegacyAPI'],
            settings['omsId'],
            settings['INN']
        ))
        self.connection.commit()  # Сохраняем изменения

    def get_current_settings(self):
        """Возвращает текущие настройки из таблицы Setting."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT PathCryptAPI, PathTrueAPI, PathLegacyAPI, omsId, INN FROM Setting WHERE id = 1")
        result = cursor.fetchone()
        if result:
            return {
                'PathCryptAPI': result[0],
                'PathTrueAPI': result[1],
                'PathLegacyAPI': result[2],
                'omsId': result[3],
                'INN': result[4]
            }
        return None

    def get_all_devices(self):
        """Возвращает все устройства из таблицы devices."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT name, token, active FROM devices")
        results = cursor.fetchall()
        return [{'name': row[0], 'token': row[1], 'active': row[2]} for row in results]

    def update_device_status(self, device_name, new_status):
        """Обновляет статус активности устройства."""
        update_sql = """
        UPDATE devices
        SET active = ?
        WHERE name = ?;
        """
        cursor = self.connection.cursor()
        cursor.execute(update_sql, (new_status, device_name))
        self.connection.commit()  # Сохраняем изменения

    def add_device(self, name, token, active):
        """Добавляет новое устройство в таблицу devices."""
        insert_sql = """
        INSERT INTO devices (name, token, active)
        VALUES (?, ?, ?);
        """
        cursor = self.connection.cursor()
        cursor.execute(insert_sql, (name, token, active))
        self.connection.commit()  # Сохраняем изменения

    def get_active_devices(self):
        """Возвращает все активные устройства из таблицы devices."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT name FROM devices WHERE active = 1")  # Получаем только активные устройства
        results = cursor.fetchall()
        return [{'name': row[0]} for row in results]

    def get_device_token(self, device_name):
        """Возвращает токен устройства по его имени."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT token FROM devices WHERE name = ?", (device_name,))
        result = cursor.fetchone()
        return result[0] if result else None  # Возвращаем токен или None, если устройство не найдено
