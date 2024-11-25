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

# Добавление нового топика
@app.route('/api//add_topic', methods=['POST'])
def add_topic():
    data = request.json
    name_topic = data.get('name_topic')
    path_topic = data.get('path_topic')
    latitude_topic = data.get('latitude_topic')
    longitude_topic = data.get('longitude_topic')

    if not name_topic or not path_topic:
        return jsonify({"error": "Поля name_topic и path_topic обязательны"}), 400

    conn = sqlite3.connect('../MQTT_Data_collector/mqtt_data.db')
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Topics (Name_Topic, Path_Topic, Latitude_Topic, Longitude_Topic) VALUES (?, ?, ?, ?)",
                   (name_topic, path_topic, latitude_topic, longitude_topic))
    conn.commit()
    conn.close()

    return jsonify({"message": "Топик успешно добавлен"}), 201

@app.route('/api//delete_topic', methods=['POST'])
def delete_topic():
    # if request.method == 'OPTIONS':
    #     response = jsonify({'message': 'Preflight check passed'})
    #     response.headers['Access-Control-Allow-Origin'] = '*'
    #     response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
    #     response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    #     return response, 200

    data = request.json
    id_topic = data.get('id_topic')

    if not id_topic:
        return jsonify({"error": "Поле id_topic обязательно"}), 400

    conn = sqlite3.connect('../MQTT_Data_collector/mqtt_data.db')
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    cursor.execute("""DELETE FROM Topics WHERE ID_Topic = ?;""", (id_topic,))  # Добавлена запятая
    conn.commit()
    conn.close()

    return jsonify({"message": "Топик успешно удален"}), 201


@app.route('/api//clear_all_tables', methods=['POST'])
def clear_all_tables():
    try:
        conn = sqlite3.connect('../MQTT_Data_collector/mqtt_data.db')
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
    conn = sqlite3.connect('../MQTT_Data_collector/mqtt_data.db')
    conn.row_factory = sqlite3.Row  # Позволяет работать с результатами как с dict
    return conn

# Метод для получения списка топиков
@app.route('/api/topics', methods=['GET'])
def get_topics():
    conn = get_db_connection()
    conn.execute('PRAGMA journal_mode=WAL')
    topics = conn.execute(
        """
        SELECT ID_Topic, Name_Topic, Path_Topic, Latitude_Topic, Longitude_Topic 
        FROM Topics
        """
    ).fetchall()
    conn.close()
    return jsonify([dict(topic) for topic in topics])

# Метод для получения данных по конкретному топику
@app.route('/api/topic_data', methods=['GET'])
def get_topic_data():
    topic_id = request.args.get('topic_id')
    if not topic_id:
        return jsonify({"error": "topic_id is required"}), 400

    conn = get_db_connection()
    conn.execute('PRAGMA journal_mode=WAL')
    data = conn.execute(
        """
        SELECT Value_Data, Time_Data 
        FROM Data 
        WHERE ID_Topic = ?
        ORDER BY Time_Data ASC
        """,
        (topic_id,)
    ).fetchall()
    conn.close()

    if not data:
        return jsonify({"error": "No data found for the topic"}), 404

    return jsonify([dict(entry) for entry in data])

@app.route('/api/topics_with_data', methods=['GET'])
def get_topics_with_data():
    conn = get_db_connection()
    conn.execute('PRAGMA journal_mode=WAL')

    # Получаем все топики
    topics = conn.execute("""
        SELECT ID_Topic, Name_Topic, Path_Topic, Latitude_Topic, Longitude_Topic
        FROM Topics
    """).fetchall()

    topics_with_data = {}

    for topic in topics:
        # Для каждого топика получаем связанные данные
        topic_id = topic['ID_Topic']
        data = conn.execute("""
            SELECT ID_Data, Value_Data, Time_Data
            FROM Data
            WHERE ID_Topic = ?
        """, (topic_id,)).fetchall()

        # Добавляем топик с данными в словарь
        topics_with_data[topic_id] = {
            "ID_Topic": topic['ID_Topic'],
            "Name_Topic": topic['Name_Topic'],
            "Path_Topic": topic['Path_Topic'],
            "Latitude_Topic": topic['Latitude_Topic'],
            "Longitude_Topic": topic['Longitude_Topic'],
            "Data": [{"ID_Data": d['ID_Data'], "Value_Data": d['Value_Data'], "Time_Data": d['Time_Data']} for d in data]
        }

    conn.close()
    return jsonify(topics_with_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9515)
