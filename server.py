"""
Flask + SQLite backend using sqlite3 (no ORM).
Features:
 - Three user types: user, worker, provider
 - JWT-based registration and login
 - Credits system and transfer helper
 - Worker credentials encrypted using Fernet

Dependencies:
    pip install Flask Flask-JWT-Extended cryptography

Usage:
    export FERNET_KEY="<your-key>"
    export JWT_SECRET_KEY="<your-jwt-secret>"
    python app.py
"""

import os
import sqlite3
from flask import Flask, request, jsonify, render_template, Response, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from cryptography.fernet import Fernet
from datetime import timedelta
import Fog
from Bot import Instance, Bot
import json

# ---------------------- Setup ----------------------
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
jwt = JWTManager(app)

FERNET_KEY = os.getenv('FERNET_KEY') or Fernet.generate_key().decode()
fernet = Fernet(FERNET_KEY.encode())

DB_PATH = 'app.db'

TEST = True

# ---------------------- Database ----------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT CHECK(role IN ('user','worker','provider')) NOT NULL,
        credits INTEGER DEFAULT 100
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS worker_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        client_secret TEXT,
        client_id TEXT,
        reddit_username TEXT,
        reddit_password TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

init_db()

# ---------------------- Helpers ----------------------
def send_credits(sender_id, receiver_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT credits FROM users WHERE id=?', (sender_id,))
    s = c.fetchone()
    c.execute('SELECT credits FROM users WHERE id=?', (receiver_id,))
    r = c.fetchone()
    if not s or not r or s[0] < amount:
        conn.close()
        return False
    c.execute('UPDATE users SET credits = credits - ? WHERE id=?', (amount, sender_id))
    c.execute('UPDATE users SET credits = credits + ? WHERE id=?', (amount, receiver_id))
    conn.commit()
    conn.close()
    return True

def decrypt_all_worker_creds():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, client_secret, client_id, reddit_username, reddit_password FROM worker_credentials')
    rows = c.fetchall()
    conn.close()

    decrypted_list = []
    for r in rows:
        try:
            decrypted_list.append({
                'user_id': r[0],
                'CLIENT_SECRET': fernet.decrypt(r[1].encode()).decode() if r[1] else '',
                'CLIENT_ID': fernet.decrypt(r[2].encode()).decode() if r[2] else '',
                'REDDIT_USERNAME': fernet.decrypt(r[3].encode()).decode() if r[3] else '',
                'REDDIT_PASSWORD': fernet.decrypt(r[4].encode()).decode() if r[4] else '',
            })
        except Exception:
            decrypted_list.append({'user_id': r[0], 'error': 'decryption failed'})
    return decrypted_list

def get_instances():
    decrypted_list = decrypt_all_worker_creds()
    instances = []
    for d in decrypted_list:
        instances.append(Instance(d['CLIENT_ID'], d['CLIENT_SECRET'], d['REDDIT_USERNAME'], d['REDDIT_PASSWORD'], d['user_id']))

FM = Fog.FogMachine(get_instances(), TEST)

# ---------------------- Routes ----------------------
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')

    if role not in ['user', 'worker', 'provider']:
        return jsonify({'msg': 'Invalid role'}), 400

    hashed = generate_password_hash(password)
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password, role) VALUES (?,?,?)',
                  (username, hashed, role))
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        return jsonify({'msg': 'Username or email already exists'}), 400

    return jsonify({'msg': 'User registered successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, password, role FROM users WHERE username=?', (username,))
    row = c.fetchone()
    conn.close()

    if not row or not check_password_hash(row[1], password):
        return jsonify({'msg': 'Invalid credentials'}), 401

    access_token = create_access_token(identity={'id': row[0], 'username': username, 'role': row[2]})
    return jsonify({'access_token': access_token})

@app.route('/', methods=['GET'])
@jwt_required()
def home():
    user = get_jwt_identity()
    if user['role'] == 'worker':
        return render_template('worker.html')
    if user['role'] == 'provider':
        return render_template('provider.html')
    return redirect('/onboarding')


@app.route('/onboarding')
def onboarding():
    return render_template('onboarding.html')

@app.route('/worker/credentials', methods=['POST'])
@jwt_required()
def upload_worker_credentials():
    user = get_jwt_identity()
    if user['role'] != 'worker':
        return jsonify({'msg': 'Only workers can upload credentials'}), 403

    data = request.json
    fields = ['CLIENT_SECRET', 'CLIENT_ID', 'REDDIT_USERNAME', 'REDDIT_PASSWORD']
    encrypted = {f.lower(): fernet.encrypt(data.get(f, '').encode()).decode() for f in fields}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO worker_credentials
                 (user_id, client_secret, client_id, reddit_username, reddit_password)
                 VALUES (?, ?, ?, ?, ?)''',
              (user['id'], encrypted['client_secret'], encrypted['client_id'], encrypted['reddit_username'], encrypted['reddit_password']))
    conn.commit()
    conn.close()

    return jsonify({'msg': 'Credentials stored securely'})

@app.route('/provider/spread_opinion', methods=['POST'])
@jwt_required()
def spread_opinion():
    op = request.json.get('op')
    post_count = request.json.get('post_count')
    comment_count = request.json.get('comment_count')
    user = get_jwt_identity()

    if user['role'] != 'provider':
        return jsonify({'msg': 'Only providers can start'}), 403

    def generate():
        # 1️⃣ Step 1 - get subreddits
        subs = FM.get_subreddits(op)
        yield f"data: {json.dumps({'subreddits': subs})}\n\n"

        # 2️⃣ Step 2 - get posts
        ps = FM.bot.get_posts(subs, post_count)
        yield f"data: {json.dumps({'posts': ps})}\n\n"

        # 3️⃣ Step 3 - get comments
        cs = FM.filter_comments(ps, comment_count, op)
        yield f"data: {json.dumps({'comments': cs})}\n\n"

        # 4️⃣ Step 4 - send replies + credits
        replies = FM.reply(cs, op)
        for reply in replies:
            send_credits(user['id'], reply[0], 5)

        yield f"data: {json.dumps({'replies': replies})}\n\n"

        # 5️⃣ Step 5 - completion notice
        yield "data: {'status': '✅ done'}\n\n"

    return Response(generate(), mimetype='text/event-stream')



if __name__ == '__main__':
    app.run(debug=True)
