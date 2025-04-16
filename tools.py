import hashlib
import os

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
