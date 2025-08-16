import hashlib
import os
from functools import wraps
from flask import jsonify, session, request

def hash_password(password):
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_or_create_secret_key(path='secret.txt'):
    if not os.path.exists(path):
        with open(path, 'wb') as f:
            key = os.urandom(32)
            f.write(key)
    else:
        with open(path, 'rb') as f:
            key = f.read()
    return key

def get_path():
    return os.path.abspath(os.path.dirname(__file__))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Необходима авторизация"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки SQL-запросов
def validate_sql(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.json
        sql = data.get('sql', '').strip().upper()
        query_type = sql.split()[0] if sql else None

        allowed_queries = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'EXECUTE']
        if query_type not in allowed_queries:
            return jsonify({
                "error": "Invalid SQL query",
                "message": f"Only {', '.join(allowed_queries)} queries are allowed"
            }), 400

        return f(*args, **kwargs)

    return decorated_function
