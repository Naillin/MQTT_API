from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# Добавление нового топика
@app.route('/add_topic', methods=['POST'])
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9515)
