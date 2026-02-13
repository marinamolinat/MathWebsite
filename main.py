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



#Some things for google oauth 
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
SCOPE = ["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"]
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "secret.json")

flow = Flow.from_client_secrets_file(client_secrets_file="secret.json", scopes=SCOPE, redirect_uri="http://127.0.0.1:8000/callback")

with open("secret.json", "r") as f:
    data = json.load(f)
    GOOGLE_CLIENT_ID = data["web"]["client_id"]
    


#login required decorator 
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "id" not in session:
            abort(401)
        return f(*args, **kwargs)
    return decorated


#Database functions
def init_db():
    connection = sqlite3.connect('database.db')

    with open('schema.sql') as f:
        connection.executescript(f.read())
    
    connection.commit()
    connection.close()

def add_student(email, firstName, lastName, grade, house):
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    #break last name into first and second last name (if applicable)
    lastNames = lastName.split(" ")

    if len(lastNames) == 1: #if they only have one last name
        cursor.execute('INSERT INTO users (email, firstName, firstLastName) VALUES (?, ?, ?)', (email, firstName, lastNames[0]))
    else: 
        cursor.execute('INSERT INTO users (email, firstName, firstLastName, secondLastName) VALUES (?, ?, ?, ?)', (email, firstName, lastNames[0], lastNames[1]))
    
    #now student table
    cursor.execute('INSERT INTO students (email, grade, house) VALUES (?, ?, ?)', (email, grade, house))

    connection.commit()
    connection.close()

def does_user_exist(email): 
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM users WHERE email = ?', (email, ))
    student = cursor.fetchone()

    connection.close()
    return student is not None


class Problem(): 
    def __init__(self, id, title, description, solution):
        self.id = id
        self.title = title
        self.description = description
        self.solution = solution
    def getStudentSolutions(self, student):
        #get the solution that the student submitted for this problem
        pass #return like a dict with info, ig


app = Flask(__name__)
app.secret_key = "will change this later lol"



#Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/oauth')
def oauth():
    
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true"
    )

    # Save state in session to verify the callback
    session["state"] = state

    return redirect(authorization_url)





@app.route('/callback')
def callback():

    flow.fetch_token(authorization_response=request.url)
    if "state" not in session or "state" not in request.args:
        abort(400)  # Bad request, missing state


    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    
    
    session["id"] = id_info.get("sub")
    session["email"] = id_info.get("email")
    session["firstName"] = id_info.get("given_name")
    session["lastName"] = id_info.get("family_name")
    session["picture"] = id_info.get("picture")


    #See if the student is new exists in the database. i.e. they are a student and need to "onboard"
    if not does_user_exist(session["email"]):
        return redirect(url_for('onboard'))


    return redirect(url_for('dashboard'))


@app.route('/onboard', methods=['GET' , 'POST'])
@login_required
def onboard():
    if request.method == 'POST':
        grade = request.form.get('grade')
        house = request.form.get('house')
        add_student(session["email"], session["firstName"], session["lastName"], grade, house)
        return redirect(url_for('dashboard'))

    return render_template('onboard.html', firstName=session['firstName'])


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=session['firstName'], profilePic=session['picture'])

@login_required
@app.route('/resources')
def resources():
    return render_template('resources.html', name=session['firstName'])

@login_required
@app.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html', name=session['firstName'])


@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('index'))

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=8000, debug=True)

