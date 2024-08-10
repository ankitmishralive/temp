from flask import Flask, redirect, url_for, render_template, session, request
from flask_cors import CORS
from dotenv import load_dotenv
from flask_graphql import GraphQLView

from tinydb import Query
import os
import requests

from werkzeug.utils import secure_filename
from datetime import datetime
import schema


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')
CORS(app)

# Keycloak Configuration
KEYCLOAK_URI = os.getenv('KEYCLOAK_URI')
REALM = os.getenv('REALM')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')



app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view(
        'graphql',
        schema=schema,
        graphiql=True
    )
)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

from db import todos_table

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def execute_graphql_query(query, variables=None):
    url = 'http://localhost:5000/graphql'
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json={'query': query, 'variables': variables})
    return response.json()

def activate_pro_license(email):
    try:
        if not email:
            return False

        User = Query()
        result = todos_table.update({'_pro_license': True}, User.email == email)

        if not result:
            return False

        return True

    except Exception as e:
        print(f"Error activating Pro License: {str(e)}")
        return False

def is_pro_user(email):
    User = Query()
    user = todos_table.get(User.email == email)
    return user and user.get('_pro_license', False)

@app.route('/todo', methods=['GET', 'POST'])
def todo():
    email = session.get('user_email')

    if request.method == 'POST':
        action = request.form['action']

        if action == 'add':
            title = request.form['title']
            description = request.form['description']
            time = request.form['time']


            try:
           
                 time = datetime.strptime(time, '%Y-%m-%dT%H:%M')
            except ValueError:
                 return "Invalid date format", 400

            images = request.files.getlist('images')
            image_paths = []
            if is_pro_user(email):
                for image in images:
                    if allowed_file(image.filename):
                        image_path = os.path.join('static', 'uploads', image.filename)
                        image.save(image_path)
                        image_paths.append(image_path)

            todos_table.insert({
                'email': email,
                'title': title,
                'description': description,
                'time': time.isoformat(),
                'images': image_paths
            })

        elif action == 'update':
            todo_id = int(request.form['todo_id'])
            title = request.form['title']
            description = request.form['description']
            time = request.form['time']

            images = request.files.getlist('images')
            image_paths = []

            try:

                 time = datetime.strptime(time, '%Y-%m-%dT%H:%M')
            except ValueError:
                 return "Invalid date format", 400
            if is_pro_user(email):
                for image in images:
                    if allowed_file(image.filename):
                        image_path = os.path.join('static', 'uploads', image.filename)
                        image.save(image_path)
                        image_paths.append(image_path)

            todos_table.update({
                'title': title,
                'description': description,
                'time': time.isoformat(),
                'images': image_paths
            }, doc_ids=[todo_id])

        elif action == 'delete':
            todo_id = int(request.form['todo_id'])
            todos_table.remove(doc_ids=[todo_id])

        return redirect(url_for('todo'))

    todos = todos_table.search(Query().email == email)
    pro_user = is_pro_user(email)
    return render_template('todo.html', todos=todos,pro_user=pro_user)

@app.route('/upload', methods=['POST'])
def upload_files():
    email = session.get('user_email')

    if is_pro_user(email):
        if 'images' not in request.files:
            return redirect(request.url)
        files = request.files.getlist('images')

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        return redirect(url_for('index'))
    else:
        return redirect(url_for('login_failed'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pro_license')
def pro_license():
    return render_template('pro_license.html')

@app.route('/payment-success')
def payment_success():
    try:
        email_or_username = session.get('user_email')
        if not email_or_username:
            return redirect(url_for('login'))

        # handling via GraphQL mutation okay all done almost
        result = activate_pro_license(email_or_username)

        if result:
            return render_template('payment_done.html')
        else:
            return "Error activating Pro License.", 500
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

@app.route('/payment-failure')
def payment_failure():
    return "Payment Failed. Please try again."

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        session['user_email'] = email

        token_url = f"{KEYCLOAK_URI}realms/{REALM}/protocol/openid-connect/token"
        token_data = {
            'grant_type': 'password',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'username': email,
            'password': password
        }
        response = requests.post(token_url, data=token_data)

        if response.status_code != 200:
            return "Failed to login", 400

        tokens = response.json()
        session['access_token'] = tokens.get('access_token')
        session['refresh_token'] = tokens.get('refresh_token')
        session['user_email'] = email

   
        User = Query()
        existing_user = todos_table.get(User.email == email)
        if not existing_user:
            # Insert the new user
            todos_table.insert({'email': email, '_pro_license': False})

        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('access_token', None)
    session.pop('refresh_token', None)
    session.pop('user_email', None)
    return redirect(url_for('index'))

@app.route('/activate_pro', methods=['POST'])
def activate_pro():
    email = session.get('user_email')
    # Activate Pro License
    activate_pro_license(email)
    return redirect(url_for('todo'))

if __name__ == '__main__':
    app.run(debug=True)
