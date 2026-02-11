from flask import Flask, render_template, request, session, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
import sqlite3
from functools import wraps
from google_auth_oauthlib.flow import Flow
import os
import pathlib
import requests
import google.auth.transport.requests
from google.oauth2 import id_token
from pip._vendor import cachecontrol
import json


os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


SCOPE = ["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"]
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "secret.json")

flow = Flow.from_client_secrets_file(client_secrets_file="secret.json", scopes=SCOPE, redirect_uri="http://localhost:8000/callback")

with open("secret.json", "r") as f:
    data = json.load(f)
    GOOGLE_CLIENT_ID = data["web"]["client_id"]
    




def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            abort(401)
        return f(*args, **kwargs)
    return decorated


def init_db():
    connection = sqlite3.connect('database.db')

    with open('schema.sql') as f:
        connection.executescript(f.read())
    
    connection.commit()
    connection.close()


def add_student(student_id, name):
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('INSERT INTO students (id, name) VALUES (?, ?)', (student_id, name))

    connection.commit()
    connection.close()

def does_student_exist(student_id):
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()

    connection.close()
    return student is not None


app = Flask(__name__)
app.secret_key = "will change this later lol"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true"
    )

    # Save state in session to verify the callback
    session["state"] = state

    print("state: ", session["state"])
    return redirect(authorization_url)


@app.route('/callback')
def callback():

    print(session)
    flow.fetch_token(authorization_response=request.url)
    if "state" not in session or "state" not in request.args:
        abort(400)  # Bad request, missing state


    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    return redirect("/")


@app.route('/login', methods=['POST', 'GET'])
def login():

    if request.method == "GET": 
        return render_template('login.html')
    else:


        id = request.form.get('username')

        session["user"] = id

        #check if pk is not in the database
        if does_student_exist(id): 
            print("back")
            return redirect(url_for('dashboard', name=id, back=True))
        
        else: 
            print("new")
            add_student(id, "test")
            return redirect(url_for('dashboard', name=id, back=False))
        



@app.route('/dashboard')
@login_required
def dashboard():
    back = request.args.get("back") == "True"


    return render_template('dashboard.html', name=request.args.get("name"), back=back)



@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('index'))

if __name__ == "__main__":
    init_db()
    app.run(host="http://localhost/", port=8000, debug=True)

