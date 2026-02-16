from flask import Flask, render_template, request, session, redirect, url_for, abort
import sqlite3
from functools import wraps
from google_auth_oauthlib.flow import Flow
import os
import requests
import google.auth.transport.requests
from google.oauth2 import id_token
from pip._vendor import cachecontrol
import json
from datetime import datetime
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url



#Some things for google oauth 
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


SCOPE = ["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"]
flow = Flow.from_client_secrets_file(client_secrets_file="secret.json", scopes=SCOPE, redirect_uri="http://127.0.0.1:8000/callback")

with open("secret.json", "r") as f:
    data = json.load(f)
    GOOGLE_CLIENT_ID = data["web"]["client_id"]
    cloudinary.config( 
    cloud_name = data["cloud"]["name"], 
    api_key = data["cloud"]["key"], 
    api_secret = data["cloud"]["secret"], 
    secure=True)
    


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


#dicty --> if you want to return a dictionary instead of a list
def executeQuery(query, params, dicty=False):


    connection = sqlite3.connect('database.db')

    if dicty: 
        connection.row_factory = sqlite3.Row 

    cursor = connection.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall()
    connection.commit()
    connection.close()

    return result



#must mantian tarsncactionality lol
#list of tuples where each tuple is (query, params)
def executeQueries(queries):
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    result = []
    for query, params in queries:
       
        cursor.execute(query, params)
        r = cursor.fetchall()
        result.append(r)
    


    connection.commit()
    connection.close()

    return result #returns a list of list of (with tuples) -> ew, i'm aware




def add_student(email, firstName, lastName, grade, house):

    #break last name into first and second last name (if applicable)
    lastNames = lastName.split(" ")
    queryList = []

    if len(lastNames) == 1: #if they only have one last name
      queryList.append(('INSERT INTO users (email, firstName, firstLastName) VALUES (?, ?, ?)', (email, firstName, lastNames[0])))
    
    else: 
       queryList.append(('INSERT INTO users (email, firstName, firstLastName, secondLastName) VALUES (?, ?, ?, ?)', (email, firstName, lastNames[0], lastNames[1])))
       
    
    #now, student table
    queryList.append(('INSERT INTO students (email, grade, house) VALUES (?, ?, ?)', (email, grade, house)))

    executeQueries(queryList)


def does_user_exist(email): 
    return executeQuery('SELECT * FROM users WHERE email = ?', (email, )) != []

def isAdmin(email):
    return executeQuery('SELECT * FROM admins WHERE email = ?', (email, )) != []


def getProblem(id): 
    result = executeQuery("SELECT * FROM mathProblems WHERE id = ?;", (id,), True)
    if result == []:
        return None
 

    return result[0]



def getGrade(email):
    return executeQuery('SELECT grade FROM students where email = ?', (email, ))[0][0]

def addProblem(title, text, file, grades, answer, deadline): 


    if answer == "":
        answer = None

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("INSERT INTO mathProblems (title, textBody, imageCDN, correctAnswer, endsAt) VALUES (?, ?, ?, ?, ?)", (title, text, file, answer, deadline))
    
    problem_id = cursor.lastrowid


    for g in grades:
        cursor.execute("INSERT INTO mathProblemsGrades (problemId, grade) VALUES (?, ?)", (problem_id, g))

    connection.commit()
    connection.close()

def getGradesProblem(id):
   r = executeQuery("SELECT grade from mathProblemsGrades WHERE problemId = ?", (id,))
   #convert it to a list of grades instead of a list of list
   result = []
   for i in r: 
    result.append(i[0])

   return result


def canStudentSubmit(probId, email):

    #Check that the problem is for the students grade level and hasn't ended 
    if getGrade(email) in getGradesProblem(probId) and getProblem(probId)["endsAt"] >= datetime.now().isoformat(timespec='minutes'):

        #check that students has not submited
        print("MAMAMAMMAM")
        print(executeQuery("SELECT * FROM studentsAnswers WHERE problemId = ? AND email = ?", (probId, email)))
       
        if executeQuery("SELECT * FROM studentsAnswers WHERE problemId = ? AND email = ?", (probId, email)) == []: 
            return True
        
    return False


#Get active problems, taking into account the grade of the student. Returns a list where index 0 represents a list of active problems, and index 1 a list inactive
def getDashboardProblems(email):
    grade = getGrade(email)
    #get id of problems that match the student's grade
    s = '''
        SELECT title, id from mathProblems, mathProblemsGrades
        WHERE mathProblemsGrades.problemId = mathProblems.id
        AND mathProblemsGrades.grade = ? 
        AND mathProblems.endsAt >= ? 
        AND mathProblems.id NOT IN (
          SELECT problemId 
          FROM studentsAnswers 
          WHERE email = ?
      )
    '''
    active = executeQuery(s, (grade, datetime.now().isoformat(timespec='minutes'), email), True)
    s = '''
       SELECT title, id FROM studentsAnswers, mathProblems
       WHERE studentsAnswers.problemId = mathProblems.id
       AND studentsAnswers.email = ?
    
    '''
    past = executeQuery(s, (email,), True)


    return active, past

def studentSubmit(email, problemId, answer):
    executeQuery("INSERT INTO studentsAnswers (problemId, email, answer) VALUES (?, ?, ?)", (problemId, email, answer))


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
    session["isAdmin"] = False
  

    #See if the student is new exists in the database. i.e. they are a student and need to "onboard"
    if not does_user_exist(session["email"]):
        return redirect(url_for('onboard'))
    
    #see if they are admin: 
    elif isAdmin(session["email"]):
        session["isAdmin"] = True
        return redirect(url_for('adminDashboard'), )

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

    #if admin
    if session["isAdmin"]:
        return render_template('adminDashboard.html', name=session['firstName'], profilePic=session['picture']) 
 

    active, past = getDashboardProblems(session["email"])
    
    return render_template('dashboard.html', name=session['firstName'], profilePic=session['picture'], activeProblems=active, pastProblem=past)



@app.route('/adminDashboard', methods=['GET' , 'POST'])
@login_required
def adminDashboard():

    if request.method == "POST":
        #addproblem
        if request.form.get("formType") == "addProblem":

            #CDN for the image
            file = request.files.get("image")
    
            filename = file.filename.lower()

            if filename != "": 
                if not filename.endswith((".png", ".jpg", ".jpeg")):
                    return "Invalid file type. Only PNG or JPEG allowed.", 400

                result = cloudinary.uploader.upload(file)
                file = result["secure_url"]
            else:
                file = None

            addProblem(title=request.form.get("title"), text=request.form.get("textbody"), file=file, grades=request.form.getlist("grades"), answer=request.form.get("answer"), deadline=request.form.get("deadline"))





    return render_template('adminDashboard.html', name=session['firstName'], profilePic=session['picture'])



@app.route("/problems/<int:probId>")
def problem(probId):


    prob = getProblem(probId)
    if prob is None:
        return "This problem does not exist.", 404

    # change endsAt to a more redable format
    endsAt = prob["endsAt"].replace('T', ' at time ')


    #check if its active (deadline hasnt finished)
    active = False
    if prob["endsAt"] > datetime.now().isoformat(timespec='minutes'):
        active = True

    #Check if user can submit (its for their grade level)
    validGrade = False
    print(getGrade(session["email"])) 
    print(getGradesProblem(prob["id"]))
    if getGrade(session["email"]) in getGradesProblem(prob["id"]):
        validGrade = True

    return render_template("problems.html", prob=prob, active=active, endsAt=endsAt, validGrade=validGrade)



@login_required
@app.route('/problems/<int:probId>/answer', methods=['POST']) 
def submitProblem(probId):


    #Check for all to be valid: 
    # 1. problem is active and can students submit it based on their grade
    if canStudentSubmit(probId, session["email"]):
        studentSubmit(email=session["email"],  problemId=probId, answer=request.form.get("answer"))
        return render_template("success.html")
    else: 
        return "sorry, something went wrong. You can't submit to this problem", 403


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

