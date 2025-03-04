from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)

# Разрешаем CORS для всех доменов
CORS(app)

# @app.before_request
# def handle_options_request():
#     if request.method == 'OPTIONS':
#         response = Flask.response_class()
#         response.headers['Access-Control-Allow-Origin'] = '*'
#         response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
#         response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
#         return response, 200
#
# @app.after_request
# def after_request(response):
#     response.headers['Access-Control-Allow-Origin'] = '*'
#     response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
#     response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
#     return response

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    login_user = data.get('login_user')
    password_user = data.get('password_user')

    if not login_user or not password_user:
        return jsonify({"error": "Поля login_user и password_user обязательны"}), 400

    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE Login_User = ? AND Password_User = ?",
                   (login_user, password_user))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"message": "Логин успешен", "user_id": user[0]}), 200
    else:
        return jsonify({"error": "Неверный логин или пароль"}), 401

# Добавление нового топика
@app.route('/api/add_topic', methods=['POST'])
def add_topic():
    data = request.json
    name_topic = data.get('name_topic')
    path_topic = data.get('path_topic')
    latitude_topic = data.get('latitude_topic')
    longitude_topic = data.get('longitude_topic')
    altitude_topic = data.get('altitude_topic')

    if not name_topic or not path_topic:
        return jsonify({"error": "Поля name_topic и path_topic обязательны"}), 400

    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Topics (Name_Topic, Path_Topic, Latitude_Topic, Longitude_Topic, Altitude_Topic) VALUES (?, ?, ?, ?, ?)",
                   (name_topic, path_topic, latitude_topic, longitude_topic, altitude_topic))
    conn.commit()
    conn.close()

    return jsonify({"message": "Топик успешно добавлен"}), 201

@app.route('/api/delete_topic', methods=['POST'])
def delete_topic():
    data = request.json
    id_topic = data.get('id_topic')

    if not id_topic:
        return jsonify({"error": "Поле id_topic обязательно"}), 400

    try:
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()

        # Удаление связанных записей из таблицы Data
        cursor.execute("""DELETE FROM Data WHERE ID_Topic = ?;""", (id_topic,))

        # Удаление связанных записей из таблицы AreaPoints
        cursor.execute("""DELETE FROM AreaPoints WHERE ID_Topic = ?;""", (id_topic,))

        # Удаление топика из таблицы Topics
        cursor.execute("""DELETE FROM Topics WHERE ID_Topic = ?;""", (id_topic,))

        conn.commit()
        conn.close()

        return jsonify({"message": "Топик и связанные записи успешно удалены"}), 201

    except sqlite3.Error as e:
        return jsonify({"error": f"Ошибка при удалении топика: {str(e)}"}), 500


@app.route('/api/clear_all_tables', methods=['POST'])
def clear_all_tables():
    try:
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()

        # Отключаем проверку внешних ключей, чтобы избежать конфликтов
        cursor.execute("PRAGMA foreign_keys = OFF;")

        # Получаем список всех таблиц
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()

        # Очищаем каждую таблицу
        for table in tables:
            cursor.execute(f"DELETE FROM {table[0]};")

        # Включаем проверку внешних ключей обратно
        cursor.execute("PRAGMA foreign_keys = ON;")

        conn.commit()
        conn.close()

        return jsonify({"message": "Все таблицы успешно очищены"}), 201
    except Exception as e:
        return jsonify({"error": f"Произошла ошибка: {str(e)}"}), 500


# Функция для подключения к БД
def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Позволяет работать с результатами как с dict
    return conn

# Метод для получения списка топиков
@app.route('/api/topics', methods=['GET'])
def get_topics():
    conn = get_db_connection()
    conn.execute('PRAGMA journal_mode=WAL')
    topics = conn.execute(
        """
            SELECT ID_Topic, Name_Topic, Path_Topic, Latitude_Topic, Longitude_Topic, Altitude_Topic, CheckTime_Topic
            FROM Topics
        """
    ).fetchall()
    conn.close()
    return jsonify([dict(topic) for topic in topics])

# Метод для получения данных по конкретному топику
@app.route('/api/topic_data', methods=['GET'])
def get_topic_data():
    # Получаем ID_Topic из параметров запроса
    topic_id = request.args.get('id_topic')
    if not topic_id:
        return jsonify({"error": "ID_Topic is required"}), 400

    conn = get_db_connection()
    conn.execute('PRAGMA journal_mode=WAL')

    # Получаем данные из таблицы Data для указанного топика
    data = conn.execute("""
        SELECT ID_Data, Value_Data, Time_Data
        FROM Data
        WHERE ID_Topic = ?
    """, (topic_id,)).fetchall()

    # Получаем массив Depression_AreaPoint из таблицы AreaPoints
    depression_points = conn.execute("""
        SELECT Depression_AreaPoint
        FROM AreaPoints
        WHERE ID_Topic = ?
    """, (topic_id,)).fetchall()

    conn.close()

    # Формируем ответ
    response = {
        "Data": [{
            "ID_Data": d['ID_Data'],
            "Value_Data": d['Value_Data'],
            "Time_Data": d['Time_Data']
        } for d in data],
        "Depression_AreaPoints": [a['Depression_AreaPoint'] for a in depression_points]
    }

    return jsonify(response)

@app.route('/api/topics_with_data', methods=['GET'])
def get_topics_with_data():
    conn = get_db_connection()
    conn.execute('PRAGMA journal_mode=WAL')

    # Получаем все топики
    topics = conn.execute("""
        SELECT ID_Topic, Name_Topic, Path_Topic, Latitude_Topic, Longitude_Topic, Altitude_Topic, CheckTime_Topic
        FROM Topics
    """).fetchall()

    topics_with_data = {}

    for topic in topics:
        topic_id = topic['ID_Topic']

        # Для каждого топика получаем связанные данные
        data = conn.execute("""
            SELECT ID_Data, Value_Data, Time_Data
            FROM Data
            WHERE ID_Topic = ?
        """, (topic_id,)).fetchall()

        area = conn.execute("""
            SELECT Depression_AreaPoint, Perimeter_AreaPoint, Included_AreaPoint, Islands_AreaPoint
            FROM AreaPoints
            WHERE ID_Topic = ?
        """, (topic_id,)).fetchall()

        # Добавляем топик с данными в словарь
        topics_with_data[topic_id] = {
            "ID_Topic": topic['ID_Topic'],
            "Name_Topic": topic['Name_Topic'],
            "Path_Topic": topic['Path_Topic'],
            "Latitude_Topic": topic['Latitude_Topic'],
            "Longitude_Topic": topic['Longitude_Topic'],
            "Altitude_Topic": topic['Altitude_Topic'],
            "CheckTime_Topic": topic['CheckTime_Topic'],
            "Data": [{
                "ID_Data": d['ID_Data'],
                "Value_Data": d['Value_Data'],
                "Time_Data": d['Time_Data']
            } for d in data],
            "Area": [{
                "Depression_AreaPoint": a['Depression_AreaPoint'],
                "Perimeter_AreaPoint": a['Perimeter_AreaPoint'],
                "Included_AreaPoint": a['Included_AreaPoint'],
                "Islands_AreaPoint": a['Islands_AreaPoint']
            } for a in area]
        }

    conn.close()
    return jsonify(topics_with_data)

db_path = '../MQTT_Data_collector/mqtt_data.db'
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9515)
