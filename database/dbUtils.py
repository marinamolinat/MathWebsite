import sqlite3
import os
from datetime import datetime



#Absolute paths 
baseDir = os.path.dirname(__file__)
dbPath = os.path.join(baseDir, "database.db")

#returnDict --> if you want to return a dictionary instead of a tuple
def executeQuery(query, params, returnDict=False):

    connection = sqlite3.connect(dbPath, timeout=5)
    
    if returnDict: 
        connection.row_factory = sqlite3.Row 
    
    try:
        cursor = connection.cursor() 
        cursor.execute("PRAGMA foreign_keys = ON") #For delete on cascade
        cursor.execute(query, params)
        result = cursor.fetchall()
        connection.commit()

    except Exception as e:
        print(f"ERROR: {e}")
        raise
    
    finally:
        connection.close() 
    
    if result == [] or result == [()]: #Instead of returning empty list or tuples, it returns None
        return None

    return result



#For transactional queries
def executeQueries(queries): #parameter queries is a list of tuples
    connection = sqlite3.connect(dbPath)
    cursor = connection.cursor()

    try:
        for query, params in queries:
            cursor.execute(query, params)

        connection.commit()
    
    except Exception as e:
        connection.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        connection.close()




        
class Student():
    def __init__(self, email):

        data = executeQuery('''
        SELECT firstName, firstLastName, profilePicURL, grade, house
        FROM users, students
        WHERE users.email = students.email
        AND users.email = ?
    ''', (email,), True)
        
        self.email = email
        self.firstName = data[0]["firstName"] if data else None
        self.lastName = data[0]["firstLastName"] if data else None
        self.picture = data[0]["profilePicURL"] if data else None
        self.grade = data[0]["grade"] if data else None
        self.house = data[0]["house"] if data else None

    @staticmethod
    def add(email, firstName, lastName, grade, house, picture):

        lastNames = lastName.split(" ") #Checks if they have a second last name (most do, some do not)
        queryList = []

        if len(lastNames) == 1: #only one last name
            queryList.append((
                'INSERT INTO users (email, firstName, firstLastName, profilePicURL) VALUES (?, ?, ?, ?)',
                (email, firstName, lastNames[0], picture)
            ))
        else: #two last names
            queryList.append((
                'INSERT INTO users (email, firstName, firstLastName, secondLastName, profilePicURL) VALUES (?, ?, ?, ?, ?)',
                (email, firstName, lastNames[0], lastNames[1], picture)
            ))
        queryList.append((
            'INSERT INTO students (email, grade, house) VALUES (?, ?, ?)',
            (email, grade, house)
        ))
        executeQueries(queryList)


    def getTotalScore(self):
        s = '''
            SELECT SUM(scoreReceived) AS totalScore
            FROM studentsAnswers
            WHERE email = ?
            GROUP BY email;

         '''
        r = executeQuery(s, (self.email, ))

        if r is not None:
            return r[0][0] #If its not none, it returns the total score (as its a list of a tuple I used indexes)
        else:
            return 0 #else, return 0 if they haven't submitted any problems yet
    

    def submit(self, problemId, answer): #student submits an answer to a problem
        executeQuery("INSERT INTO studentsAnswers (problemId, email, answer) VALUES (?, ?, ?)", (problemId, self.email, answer))
    
    def getResponse(self, problemId): #get answer to a spefic problem
        r = executeQuery("SELECT answer FROM studentsAnswers WHERE problemId = ? AND email = ?", (problemId, self.email), True)

        if r is not None:
            r = r[0][0] #again, indexes are used as a tuple inside a list is returned by executeQuery
        return r

    

    #Get active problems, taking into account the grade of the student. Returns a list where index 0 represents a list of active problems, and index 1 a list inactive
    def getDashboardProblems(self):
        
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
        active = executeQuery(s, (self.grade, datetime.now().isoformat(timespec='minutes'), self.email), True)
        s = '''
        SELECT title, id, scoreReceived FROM studentsAnswers, mathProblems
        WHERE studentsAnswers.problemId = mathProblems.id
        AND studentsAnswers.email = ?
        '''
        past = executeQuery(s, (self.email,), True)

        if past is None:
            past = [] #must be a list because Jinja iterated over this return 
        if active is None:
            active = []  #must be a list because Jinja iterated over this return 
        return active, past
    
    def canStudentSubmit(self, probId):
        r = executeQuery('''
            SELECT 1
            FROM mathProblems, mathProblemsGrades
            WHERE mathProblems.id = mathProblemsGrades.problemId
            AND mathProblems.id = ?
            AND mathProblemsGrades.grade = ?
            AND mathProblems.endsAt >= ?
            AND NOT EXISTS (
                SELECT 1 FROM studentsAnswers 
                WHERE problemId = ? AND email = ?
            )
        ''', (probId, self.grade, datetime.now().isoformat(timespec='minutes'), probId, self.email))
    
        return r is not None
    def getScore(self, probId):
        r = '''
        SELECT scoreReceived FROM studentsAnswers
        WHERE problemId = ?
        AND email = ?
        '''
        r = executeQuery(r, (probId, self.email))
        if r is not None:
            r = r[0][0]
        return r
        
    
  
class Problem():
    def __init__(self, probId):
            self.probId = probId
            data = executeQuery("SELECT * FROM mathProblems WHERE id = ?;", (probId,), True)
            self.title = data[0]["title"] if data else None
            self.text = data[0]["textBody"] if data else None
            self.image = data[0]["imageURL"] if data else None
            self.correctAnswer = data[0]["correctAnswer"] if data else None
            self.pointsIfCorrect = data[0]["pointsIfCorrect"] if data else None
            self.endsAt = data[0]["endsAt"] if data else None


    @staticmethod
    def getAll():
        s = '''
            SELECT 
            mathProblems.id,
            mathProblems.title,
            COUNT(studentsAnswers.email) AS numAnswers
            FROM mathProblems
            LEFT JOIN studentsAnswers ON mathProblems.id = studentsAnswers.problemId
            GROUP BY mathProblems.id, mathProblems.title
                
        '''
        r = executeQuery(s, (), True)
        if r is None: 
            r = []

        return r
    




    @staticmethod
    def add(title, text, file, grades, answer, pointsIfCorrect, deadline):
        connection = sqlite3.connect(dbPath)
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO mathProblems (title, textBody, imageURL, correctAnswer, pointsIfCorrect, endsAt) VALUES (?, ?, ?, ?, ?, ?)",
            (title, text, file, answer, pointsIfCorrect, deadline)
        )
        problemId = cursor.lastrowid
        for g in grades:
            cursor.execute("INSERT INTO mathProblemsGrades (problemId, grade) VALUES (?, ?)", (problemId, g))
        connection.commit()
        connection.close()


    def isActive(self):
        if not self._data:
            return False
        return self._data["endsAt"] > datetime.now().isoformat(timespec='minutes')

    def grades(self):
        r = executeQuery("SELECT grade FROM mathProblemsGrades WHERE problemId = ?", (self.probId,))
        grades = []
        for row in r:
            grades.append(row[0])

        return grades #Rreturns a list of ints (the grades)

    def numAnswers(self):  #Number of answeres of a problem
        return executeQuery(
            "SELECT COUNT(*) FROM studentsAnswers WHERE problemId = ?",
            (self.probId,)
        )[0][0]

    def getAllStudentAnswers(self): #returns a list of dictionaries for all student answers to the problem
        return executeQuery('''
            SELECT firstName, firstLastName, answer, scoreReceived, students.email
            FROM studentsAnswers, students, users
            WHERE students.email = studentsAnswers.email
            AND users.email = students.email
            AND studentsAnswers.problemId = ?
        ''', (self.probId,), True)

    def canStudentSubmit(self, email):
        r = '''
             SELECT 1
            FROM mathProblems, mathProblemsGrades, students
            WHERE mathProblems.id = mathProblemsGrades.problemId
            AND mathProblemsGrades.grade = students.grade
            AND students.email = ?
            AND mathProblems.id = ?
            AND mathProblems.endsAt >= ?
            AND NOT EXISTS (
            SELECT 1 FROM studentsAnswers 
            WHERE problemId = ? AND email = ?
            )
        '''
        result = executeQuery(r, (email, self.probId, datetime.now().isoformat(timespec='minutes'), self.probId, email))
        return result is not None #If its not None, return True, otherwise, return False 
    
    def changeScore(self, email, score): #Change score of student
        r = '''
            UPDATE studentsAnswers
            SET scoreReceived = ?
            WHERE problemId = ? AND email = ?
        '''
        executeQuery(r, (score, self.probId, email))

    def delete(self):
        executeQuery(" DELETE FROM mathProblems WHERE id = ?", (self.probId,))

    def autoGrade(self):
        executeQuery('''
            UPDATE studentsAnswers
            SET scoreReceived = CASE
                WHEN answer = (SELECT correctAnswer FROM mathProblems WHERE id = problemId)
                THEN (SELECT pointsIfCorrect FROM mathProblems WHERE id = problemId)
                ELSE 0
            END
            WHERE problemId = ?;
        ''', (self.probId,))


    


#Simple isAdmin
def isAdmin(email):
    return executeQuery('SELECT * FROM admins WHERE email = ?', (email,)) is not None

#For The leaderboard
def getLeaderboardStudents(grade=None):

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
    
    if r is None:
        r = []
    
    return r

def getLeaderboardHouse(grade=None):
    if grade is None:
        s = '''
            SELECT students.house,
            SUM(studentsAnswers.scoreReceived) AS totalScore
            FROM students, studentsAnswers
            WHERE students.email = studentsAnswers.email
            GROUP BY students.house
            ORDER BY totalScore DESC
        '''
        r = executeQuery(s, (), True)
    else:
        s = '''
            SELECT students.house,
            SUM(studentsAnswers.scoreReceived) AS totalScore
            FROM students, studentsAnswers
            WHERE students.email = studentsAnswers.email
            AND students.grade = ?
            GROUP BY students.house
            ORDER BY totalScore DESC
        '''
   
        r = executeQuery(s, (grade,), True)

    if r is None:
        r = []
    return r