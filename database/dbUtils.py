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


#returnDict --> if you want to return a dictionary instead of a list
def executeQuery(query, params, returnDict=False):

    connection = sqlite3.connect(dbPath, timeout=5)
    
    if returnDict: 
        connection.row_factory = sqlite3.Row 
    
    try:
        cursor = connection.cursor() 
        cursor.execute(query, params)
        result = cursor.fetchall()
        connection.commit()

    except Exception as e:
        print(f"ERROR: {e}")
        raise
    
    finally:
        connection.close() 
    
    if result == []:
        return None

    return result



#Transactionality
def executeQueries(queries):
    connection = sqlite3.connect(dbPath)
    cursor = connection.cursor()
    result = []
    try:
        for query, params in queries:
            cursor.execute(query, params)
            r = cursor.fetchall()
            result.append(r)
        connection.commit()
    except Exception as e:
        connection.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        connection.close()
    return result



        
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
        lastNames = lastName.split(" ")
        queryList = []
        if len(lastNames) == 1:
            queryList.append((
                'INSERT INTO users (email, firstName, firstLastName, profilePicURL) VALUES (?, ?, ?, ?)',
                (email, firstName, lastNames[0], picture)
            ))
        else:
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
            return r[0][0]
        else:
            return 0
    
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
            past = []
        if active is None:
            active = []

        return active, past
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
        
    
    def submit(self, problemId, answer):
        executeQuery("INSERT INTO studentsAnswers (problemId, email, answer) VALUES (?, ?, ?)", (problemId, self.email, answer))
    
    def getResponse(self, problemId):
        r = executeQuery("SELECT answer FROM studentsAnswers WHERE problemId = ? AND email = ?", (problemId, self.email), True)
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


    def isActive(self):
        if not self._data:
            return False
        return self._data["endsAt"] > datetime.now().isoformat(timespec='minutes')

    def grades(self):
        r = executeQuery("SELECT grade FROM mathProblemsGrades WHERE problemId = ?", (self.probId,))
        grades = []
        for row in r:
            grades.append(row[0])

        return grades

    def numAnswers(self):
        return executeQuery(
            "SELECT COUNT(*) FROM studentsAnswers WHERE problemId = ?",
            (self.probId,)
        )[0][0]

    def getAllStudentAnswers(self):
        return executeQuery('''
            SELECT firstName, firstLastName, answer, scoreReceived, students.email
            FROM studentsAnswers, students, users
            WHERE students.email = studentsAnswers.email
            AND users.email = students.email
            AND studentsAnswers.problemId = ?
        ''', (self.probId,), True)

    def canStudentSubmit(self, email):
        r = '''
             SELECT *
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
        return result is not None
    
    def changeScore(self, email, score):
        r = '''
            UPDATE studentsAnswers
            SET scoreReceived = ?
            WHERE problemId = ? AND email = ?
        '''
        executeQuery(r, (score, self.probId, email))

    def delete(self):
        executeQuery("DELETE FROM mathProblems WHERE id = ?", (self.probId,))

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

    @staticmethod
    def add(title, text, file, grades, answer, pointsIfCorrect, deadline):
        if answer == "":
            answer = None
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
        return executeQuery(s, (), True)
    


#Simple isAdmin
def isAdmin(email):
    return executeQuery('SELECT * FROM admins WHERE email = ?', (email,)) is not None

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
    
    if r is None:
        r = []
    
    return r

