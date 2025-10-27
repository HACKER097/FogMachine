from flask import Flask, render_template, request, jsonify, Response, g
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, JWTManager
import sqlite3
import bcrypt
import os
from dotenv import load_dotenv
import json
import AI

load_dotenv()

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret")  # Change this!
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = False # Should be True in production
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
jwt = JWTManager(app)

DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# --- Database Creation ---
@app.cli.command('init-db')
def init_db_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


# --- Routes ---

@app.route('/')
@jwt_required(optional=True)
def index():
    current_user_json = get_jwt_identity()
    print(f"current_user_json: {current_user_json}")
    if not current_user_json:
        return render_template('onboarding.html')

    current_identity = json.loads(current_user_json)
    role = current_identity.get('role')
    if role == 'provider':
        return render_template('provider.html')
    elif role == 'worker':
        return render_template('worker.html')
    else:
        return render_template('onboarding.html')


@app.route('/onboarding')
def onboarding():
    return render_template('onboarding.html')


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    if not username or not password or not role:
        return jsonify({"msg": "Username, password, and role are required"}), 400

    if role not in ['worker', 'provider']:
        return jsonify({"msg": "Invalid role"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        return jsonify({"msg": "Username already exists"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                   (username, hashed_password, role))
    db.commit()

    return jsonify({"msg": "User registered successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        identity = {'username': user['username'], 'role': user['role'], 'id': user['id']}
        access_token = create_access_token(identity=json.dumps(identity))
        response = jsonify({"msg": "login successful"})
        from flask_jwt_extended import set_access_cookies
        set_access_cookies(response, access_token)
        return response

    return jsonify({"msg": "Bad username or password"}), 401

@app.route("/logout", methods=["POST"])
def logout():
    from flask_jwt_extended import unset_jwt_cookies
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response


from Fog import FogMachine, instances as fog_instances
from Bot import Instance

# --- Worker Routes ---
@app.route('/worker/credentials', methods=['POST'])
@jwt_required()
def add_credentials():
    current_user_json = get_jwt_identity()
    current_user = json.loads(current_user_json)
    if current_user['role'] != 'worker':
        return jsonify({"msg": "Workers only"}), 403

    data = request.get_json()
    client_id = data.get('CLIENT_ID')
    client_secret = data.get('CLIENT_SECRET')
    reddit_username = data.get('REDDIT_USERNAME')
    reddit_password = data.get('REDDIT_PASSWORD')

    if not all([client_id, client_secret, reddit_username, reddit_password]):
        return jsonify({"msg": "All fields are required"}), 400

    db = get_db()
    db.execute(
        'INSERT INTO credentials (user_id, client_id, client_secret, reddit_username, reddit_password) VALUES (?, ?, ?, ?, ?)',
        (current_user['id'], client_id, client_secret, reddit_username, reddit_password)
    )
    db.commit()

    return jsonify({"msg": "Credentials saved successfully"}), 201

# --- Provider Routes ---
@app.route('/provider/spread_opinion', methods=['POST'])
@jwt_required()
def spread_opinion_route():
    current_user_json = get_jwt_identity()
    current_user = json.loads(current_user_json)
    if current_user['role'] != 'provider':
        return jsonify({"msg": "Providers only"}), 403

    data = request.get_json()
    op = data.get('op')

    if not op:
        return jsonify({"msg": "Opinion is required"}), 400

    def generate_logs():
        try:
            fog_machine = FogMachine(fog_instances, os.getenv("TEST"))
            subreddits = fog_machine.get_subreddits(op)
            yield f"data: {json.dumps({'status': 'Found subreddits', 'subreddits': subreddits})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'Error', 'message': str(e)})}\n\n"

    return Response(generate_logs(), mimetype='text/event-stream')


@app.route('/provider/continue_campaign', methods=['POST'])
@jwt_required()
def continue_campaign_route():
    current_user_json = get_jwt_identity()
    current_user = json.loads(current_user_json)
    if current_user['role'] != 'provider':
        return jsonify({"msg": "Providers only"}), 403

    data = request.get_json()
    op = data.get('op')
    post_count = data.get('post_count', 10)
    comment_count = data.get('comment_count', 10)
    subreddits = data.get('subreddits')

    if not op or not subreddits:
        return jsonify({"msg": "Opinion and subreddits are required"}), 400

    db = get_db()
    # Create a new campaign
    cursor = db.execute(
        'INSERT INTO campaigns (provider_id, opinion, post_count, comment_count, status) VALUES (?, ?, ?, ?, ?)',
        (current_user['id'], op, post_count, comment_count, 'running')
    )
    campaign_id = cursor.lastrowid
    db.commit()

    def generate_logs():
        try:
            with app.app_context():
                db = get_db()
                cursor = db.execute('SELECT * FROM credentials')
                creds = cursor.fetchall()

                instances = []
                for cred in creds:
                    instances.append(Instance(
                        client_id=cred['client_id'],
                        client_secret=cred['client_secret'],
                        username=cred['reddit_username'],
                        password=cred['reddit_password'],
                        userid=cred['user_id']
                    ))

                if not instances:
                    raise Exception("No worker credentials found.")

                fog_machine = FogMachine(instances, os.getenv("TEST"))
                for log_message in fog_machine.spread_opinion(op, post_count, comment_count, subreddits):
                    yield f"data: {json.dumps(log_message)}\n\n"

                db = get_db()
                db.execute('UPDATE campaigns SET status = ? WHERE id = ?', ('completed', campaign_id))
                db.commit()
                yield f"data: {json.dumps({'status': 'Campaign completed successfully!'})}\n\n"

        except Exception as e:
            with app.app_context():
                db = get_db()
                db.execute('UPDATE campaigns SET status = ? WHERE id = ?', ('failed', campaign_id))
                db.commit()
                yield f"data: {json.dumps({'status': 'Error', 'message': str(e)})}\n\n"

    return Response(generate_logs(), mimetype='text/event-stream')



if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        with app.app_context():
            init_db()
            print('Initialized the database.')
    app.run(debug=True, threaded=True)
