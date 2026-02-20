from flask import Flask, render_template, request, session, redirect, url_for, abort
from functools import wraps

from datetime import datetime

import os
import requests

#Google Oauth
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
from google.oauth2 import id_token
from pip._vendor import cachecontrol

#Cloudinary
import cloudinary
import cloudinary.uploader

import json

from database.dbUtils import *


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
    flaskSecret = data['flask']['secret']

    


#login required decorator 
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "email" not in session:
            abort(401)
        return f(*args, **kwargs)
    return decorated


app = Flask(__name__)
app.secret_key = flaskSecret


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

    # Save state in session to verify callback
    session["state"] = state

    return redirect(authorization_url)



@app.route('/callback')
def callback():

    flow.fetch_token(authorization_response=request.url)
    if "state" not in session or "state" not in request.args:
        abort(400) 


    if not session["state"] == request.args["state"]:
        abort(500)  

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    #Session info 
    session["email"] = id_info.get("email")
    session["firstName"] = id_info.get("given_name")
    session["lastName"] = id_info.get("family_name")
    session["picture"] = id_info.get("picture")
    session["isAdmin"] = False


    #see if they are admin: 
    if isAdmin(session["email"]):
        session["isAdmin"] = True
        return redirect(url_for('adminDashboard'), )
    
    #See if the user exists in the database. If they do not, they are a student and need to "onboard"
    elif not does_user_exist(session["email"]):
        return redirect(url_for('onboard'))


    return redirect(url_for('dashboard'))


@app.route('/onboard', methods=['GET' , 'POST'])
@login_required
def onboard():
    if request.method == 'POST':
        grade = request.form.get('grade')
        house = request.form.get('house')
        add_student(session["email"], session["firstName"], session["lastName"], grade, house, session['picture'])
        return redirect(url_for('dashboard'))

    return render_template('onboard.html', firstName=session['firstName'])


@app.route('/dashboard')
@login_required
def dashboard():
 

    #if admin
    if session["isAdmin"]:
        return redirect(url_for('adminDashboard'))
    


    active, past = getDashboardProblems(session["email"])
    
    return render_template('dashboard.html', name=session['firstName'], profilePic=session['picture'], activeProblems=active, pastProblems=past, score=getStudentTotalScore(session['email']))



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

    
            addProblem(title=request.form.get("title"), text=request.form.get("textbody"), file=file, grades=request.form.getlist("grades"), answer=request.form.get("answer"), pointsIfCorrect=request.form.get("pointsIfCorrect"), deadline=request.form.get("deadline"))
            ##revise 
            return redirect(url_for('success', title='Success! The problem has been added'))
           

  
    sqlProblems = getAllProblems()
        
    problems = []
    for row in sqlProblems:
        p = dict(row)
        p["numAnswers"] = getNumAnswers(p["id"])
        problems.append(p)


    return render_template('adminDashboard.html', name=session['firstName'], profilePic=session['picture'], problems=problems)



@app.route("/problems/<int:probId>", methods=['GET' , 'POST', 'DELETE', 'PATCH'])
def problem(probId):



    if request.method == 'DELETE':
        if session['isAdmin']:
            deleteProblem(probId)
            return redirect(url_for('success', title='Success! The problem has been deleted'), code=303)
        else: 
            abort(403)


    prob = getProblem(probId)

    if request.method == 'PATCH':
        
        #server side validation
        if session['isAdmin']:
        
            score = request.form.get("score")

            try:
                score = float(score)
                if score >= 0 and score <= prob['pointsIfCorrect']:
                    changeScore(score=score, email=request.form.get("email"), probId=probId)

               
            except ValueError:
                abort(400)
                
               
        else: 
            abort(403)





    studentAnswer = getStudentAnswer(probId, session['email'])
    if prob is None:
        return "This problem does not exist.", 404

    # change endsAt to a more redable format
    endsAt = prob["endsAt"].replace('T', ' at time ')


    #check if student can submit (hasn't submitted yet, deadline hasn't passed, correct grade)
    canSubmit = False
    if canStudentSubmit(probId, session["email"]) and not session["isAdmin"]:
        canSubmit = True
    
    grades = getGradesProblem(probId)

    active = False
    if prob["endsAt"] > datetime.now().isoformat(timespec='minutes'):
        active = True

    return render_template("problems.html", prob=prob, canSubmit=canSubmit, endsAt=endsAt, grades=grades, active=active, isAdmin=session["isAdmin"],   numAnswers=getNumAnswers(probId), studentAnswer=studentAnswer, students=getAllStudentAnswers(probId))


@login_required
@app.route('/problems/<int:probId>/autograde', methods=['POST'])
def gradeProblem(probId):
   
    
    if request.form.get("autoGrade"):
        autoGrade(probId)
        return redirect(url_for("success", title='Nice! Problems have been autograded', subtitle=':)'))
       

    



@login_required
@app.route('/success')     
def success():
    return render_template("success.html", title=request.args.get("title"), subtitle=request.args.get("subtitle"))



@login_required
@app.route('/problems/<int:probId>/answer', methods=['POST']) 
def submitProblem(probId):


    #Check for all to be valid: 
    # 1. problem is active and can students submit it based on their grade
    if canStudentSubmit(probId, session["email"]):
        studentSubmit(email=session["email"],  problemId=probId, answer=request.form.get("answer"))

        return redirect(url_for("success", title='Nice! You have submited your problem', subtitle='Wait a few days for it to be graded and for you to receive your score!'))
    else: 
        return "sorry, something went wrong. You can't submit to this problem", 403



@login_required
@app.route('/leaderboard')
def leaderboard():

  
    
    r = (request.args.get("grade"))

    if r in ['5', '6', '7', '8', '9', '10', '11']:
        r = int(r)
    else: 
        r = None

    return render_template('leaderboard.html', name=session['firstName'], students=getLeaderboardInfo(r))


@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('index'))

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=8000, debug=True)

