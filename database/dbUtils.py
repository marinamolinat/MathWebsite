import sqlite3
import os
from datetime import datetime



BASE_DIR = os.path.dirname(__file__)
schemaPath = os.path.join(BASE_DIR, "schema.sql")
dbPath = os.path.join(BASE_DIR, "database.db")



#Database functions
def init_db():
    connection = sqlite3.connect(dbPath)

    with open(schemaPath) as f:
        connection.executescript(f.read())
    
    connection.commit()
    connection.close()


#dicty --> if you want to return a dictionary instead of a list
def executeQuery(query, params, dicty=False):


    connection = sqlite3.connect(dbPath)

    if dicty: 
        connection.row_factory = sqlite3.Row 

    cursor = connection.cursor() 
    cursor.execute(query, params)
    result = cursor.fetchall()
    connection.commit()
    connection.close()

    return result

def deleteProblem(probId):
    executeQuery("DELETE FROM mathProblems WHERE id = ?", (probId,))

#must mantian tarsncactionality lol
#list of tuples where each tuple is (query, params)
def executeQueries(queries):
    connection = sqlite3.connect(dbPath)
    cursor = connection.cursor()
    result = []
    for query, params in queries:
       
        cursor.execute(query, params)
        r = cursor.fetchall()
        result.append(r)
    


    connection.commit()
    connection.close()

    return result #returns a list of list of (with tuples) -> ew, i'm aware

def getStudentTotalScore(email):
    s = '''
            SELECT SUM(scoreReceived) AS totalScore
            FROM studentsAnswers
            WHERE email = ?
            GROUP BY email;

    '''
    r = executeQuery(s, (email, ))
    if r != []:
        return r[0][0]




def add_student(email, firstName, lastName, grade, house, profilePic):

    #break last name into first and second last name (if applicable)
    lastNames = lastName.split(" ")
    queryList = []

    if len(lastNames) == 1: #if they only have one last name
      queryList.append(('INSERT INTO users (email, firstName, firstLastName, profilePicURL) VALUES (?, ?, ?, ?)', (email, firstName, lastNames[0], profilePic)))
    
    else: 
       queryList.append(('INSERT INTO users (email, firstName, firstLastName, secondLastName,  profilePicURL) VALUES (?, ?, ?, ?, ?)', (email, firstName, lastNames[0], lastNames[1], profilePic)))
       
    
    #now, student table
    queryList.append(('INSERT INTO students (email, grade, house) VALUES (?, ?, ?)', (email, grade, house)))

    executeQueries(queryList)


def does_user_exist(email): 
    return executeQuery('SELECT * FROM users WHERE email = ?', (email, )) != []

def isAdmin(email):
    return executeQuery('SELECT * FROM admins WHERE email = ?', (email, )) != []


def getProblem(probId): 
 
    result = executeQuery("SELECT * FROM mathProblems WHERE id = ?;", (probId,), True)
    if result == []:
        return None
 

    return result[0]






def getGrade(email):
    r = executeQuery('SELECT grade FROM students where email = ?', (email, ))
    if r != []:
        return r[0][0]
    return None

def addProblem(title, text, file, grades, answer, pointsIfCorrect, deadline): 


    if answer == "":
        answer = None

    connection = sqlite3.connect(dbPath)
    cursor = connection.cursor()

    cursor.execute("INSERT INTO mathProblems (title, textBody, imageURL, correctAnswer, pointsIfCorrect, endsAt) VALUES (?, ?, ?, ?, ?, ?)", (title, text, file, answer, pointsIfCorrect, deadline))
    
    problem_id = cursor.lastrowid


    for g in grades:
        cursor.execute("INSERT INTO mathProblemsGrades (problemId, grade) VALUES (?, ?)", (problem_id, g))

    connection.commit()
    connection.close()

def autoGrade(probId):
  
    executeQuery(
        '''
        UPDATE studentsAnswers
        SET scoreReceived = CASE 
            WHEN answer = (SELECT correctAnswer FROM mathProblems WHERE id = problemId)
            THEN (SELECT pointsIfCorrect FROM mathProblems WHERE id = problemId)
            ELSE 0
        END
        WHERE problemId = ?;
        
            ''', (probId,)
    )
    print("DONE EFUHEIWUHFAEW EXECUTED")


def getGradesProblem(probId):
   r = executeQuery("SELECT grade from mathProblemsGrades WHERE problemId = ?", (probId,))
   #convert it to a list of grades instead of a list of list
   result = []
   for i in r: 
    result.append(i[0])

   return result


def canStudentSubmit(probId, email):

    #Check that the problem is for the students grade level and hasn't ended 
    if getGrade(email) in getGradesProblem(probId) and getProblem(probId)["endsAt"] >= datetime.now().isoformat(timespec='minutes'):

        #check that students has not submited
        print(executeQuery("SELECT * FROM studentsAnswers WHERE problemId = ? AND email = ?", (probId, email)))
       
        if executeQuery("SELECT * FROM studentsAnswers WHERE problemId = ? AND email = ?", (probId, email)) == []: 
            return True
        
    return False


#Get active problems, taking into account the grade of the student. Returns a list where index 0 represents a list of active problems, and index 1 a list inactive
def getDashboardProblems(email):
    grade = getGrade(email)
    #get id of problems that match the student's grade
    s = '''
        SELECT title, id FROM mathProblems, mathProblemsGrades
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
       SELECT title, id, scoreReceived FROM studentsAnswers, mathProblems
       WHERE studentsAnswers.problemId = mathProblems.id
       AND studentsAnswers.email = ?
    


    '''
    past = executeQuery(s, (email,), True)


    return active, past

def studentSubmit(email, problemId, answer):
    executeQuery("INSERT INTO studentsAnswers (problemId, email, answer) VALUES (?, ?, ?)", (problemId, email, answer))


def getAllProblems():
   return executeQuery("SELECT title, id FROM mathProblems", (), True)



def getStudentAnswer(probId, email):
    r =  executeQuery("SELECT * FROM studentsAnswers WHERE problemId = ? AND email = ?", (probId, email), True)
    if r != []:
        print(r)
        return r[0]
    
    return None


#For The leaderboard
def getLeaderboardInfo(grade=None):

    if grade == None:

        s = '''
            SELECT users.firstName, users.firstLastName, users.profilePicURL, students.house,
            SUM(studentsAnswers.scoreReceived) AS totalScore
            FROM users, students, studentsAnswers
            WHERE users.email = students.email
            AND students.email = studentsAnswers.email
            GROUP BY users.email, users.firstName, users.firstLastName, users.profilePicURL, students.house
            ORDER BY totalScore DESC;
        '''
        r = executeQuery(s, (), True)

    else: 
        s = '''
        SELECT users.firstName, users.firstLastName, users.profilePicURL, students.house,
            SUM(studentsAnswers.scoreReceived) AS totalScore
            FROM users, students, studentsAnswers
            WHERE users.email = students.email
            AND students.email = studentsAnswers.email
            AND students.grade = ?
            GROUP BY users.email, users.firstName, users.firstLastName, users.profilePicURL, students.house
            ORDER BY totalScore DESC;
            '''
        r = executeQuery(s, (grade,), True)
    

    return r

def getAllStudentAnswers(probId):
    s = '''
        SELECT firstName, firstLastName, answer, scoreReceived, students.email
        FROM studentsAnswers, students, users
        WHERE students.email = studentsAnswers.email
        AND users.email = students.email
        AND studentsAnswers.problemId = ?
        '''
     
    return executeQuery(s, (probId,), True)

def  changeScore(score, email, probId):
    s = '''

    UPDATE studentsAnswers
    SET scoreReceived = ?
    WHERE problemId = ?
    AND email = ?
    '''
    return executeQuery(s, (score, probId, email))


def getNumAnswers(probId):
    return executeQuery("SELECT COUNT(*) FROM studentsAnswers WHERE problemId = ?", (probId, ))[0][0]
