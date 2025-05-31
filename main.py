from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_session import Session
import sqlite3
from tools import hash_password, get_or_create_secret_key, get_path, login_required
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta
import os

SESSION_TIME = 2
app = Flask(__name__)

# Ключ в файле
app.secret_key = get_or_create_secret_key()


db_sessions_path = os.path.join(get_path(), 'api_sessions.db')
# Подключаем SQLite (можно общий с твоими данными)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_sessions_path}'  # путь рядом с main.py
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'  # любое имя
app.config['SESSION_PERMANENT'] = False
#app.permanent_session_lifetime = timedelta(hours=SESSION_TIME)

# Настраиваем БД и сессии
db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db
Session(app)

# Инициализируем таблицу, если её нет
with app.app_context():
    db.create_all()

# Разрешаем CORS для всех доменов
CORS(app, supports_credentials=True)

@app.route('/api/check-auth')
def check_auth():
    if 'user_id' in session:
        return '', 200  # Просто пустой 200 — достаточно
    return '', 401  # Без JSON, просто код

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    login_user = data.get('login_user')
    password_user = data.get('password_user')

    if not login_user or not password_user:
        return jsonify({"error": "Поля login_user и password_user обязательны"}), 400

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()

        # Получаем пользователя и хеш пароля из БД
        cursor.execute("SELECT ID_User, Password_User FROM Users WHERE Login_User = ?",
                       (login_user,))
        user = cursor.fetchone()

        if user and user[1] == password_user:
            # Сохраняем ID пользователя в сессии
            session['user_id'] = user[0]
            return jsonify({
                "message": "Логин успешен",
                "user_id": user[0]
            }), 200
        else:
            return jsonify({"error": "Неверный логин или пароль"}), 401

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/logout')
@login_required
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logged out"}), 200

# Добавление нового топика
@app.route('/api/add_topic', methods=['POST'])
@login_required
def add_topic():
    data = request.json
    name_topic = data.get('name_topic')
    path_topic = data.get('path_topic')
    latitude_topic = data.get('latitude_topic')
    longitude_topic = data.get('longitude_topic')
    altitude_topic = data.get('altitude_topic')
    altitude_sensor_topic = data.get('altitude_sensor_topic')

    if not name_topic or not path_topic:
        return jsonify({"error": "Поля name_topic и path_topic обязательны"}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Topics (Name_Topic, Path_Topic, Latitude_Topic, Longitude_Topic, Altitude_Topic) VALUES (?, ?, ?, ?, ?)",
                   (name_topic, path_topic, latitude_topic, longitude_topic, altitude_topic))
    conn.commit()
    conn.close()

    return jsonify({"message": "Топик успешно добавлен"}), 201

@app.route('/api/delete_topic', methods=['POST'])
@login_required
def delete_topic():
    data = request.json
    id_topic = data.get('id_topic')

    if not id_topic:
        return jsonify({"error": "Поле id_topic обязательно"}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
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
@login_required
def clear_all_tables():
    try:
        conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Позволяет работать с результатами как с dict
    return conn

# Метод для получения списка топиков
@app.route('/api/topics', methods=['GET'])
@login_required
def get_topics():
    conn = get_db_connection()
    conn.execute('PRAGMA journal_mode=WAL')
    topics = conn.execute(
        """
            SELECT ID_Topic, Name_Topic, Path_Topic, Latitude_Topic, Longitude_Topic, Altitude_Topic, AltitudeSensor_Topic, CheckTime_Topic
            FROM Topics
        """
    ).fetchall()
    conn.close()
    return jsonify([dict(topic) for topic in topics])

# Метод для получения данных по конкретному топику
@app.route('/api/topic_data', methods=['GET'])
@login_required
def get_topic_data():
    # Получаем ID_Topic из параметров запроса
    topic_id = request.args.get('id_topic')
    if not topic_id:
        return jsonify({"error": "ID_Topic is required"}), 400

    # Получаем лимит (если передан и корректен)
    limit = None
    if 'limit' in request.args:
        try:
            limit = int(request.args.get('limit'))
            if limit <= 0:  # Если 0 или отрицательное — игнорируем
                limit = None
        except ValueError:  # Если не число (например, limit=abc)
            pass  # Оставляем limit = None

    conn = get_db_connection()
    conn.execute('PRAGMA journal_mode=WAL')

    # Основной запрос данных
    data_query = """
        SELECT ID_Data, Value_Data, Time_Data
        FROM Data
        WHERE ID_Topic = ?
        ORDER BY Time_Data DESC
    """
    params = (topic_id,)

    # Добавляем LIMIT только если указан и > 0
    if limit is not None:
        data_query += " LIMIT ?"
        params += (limit,)

    data = conn.execute(data_query, params).fetchall()
    # Разворачиваем данные (меняем порядок на возрастание времени)
    data = data[::-1]  # Это развернет список

    # Запрос Depression_AreaPoints (без изменений)
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
@login_required
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
            "AltitudeSensor_Topic": topic['AltitudeSensor_Topic'],
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

DB_PATH = '../MQTT_Data_collector/mqtt_data.db'
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9515)
