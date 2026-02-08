from flask import Flask, render_template, request, sessions, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import sqlite3



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

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == "GET": 
        return render_template('login.html')
    else:
        id = request.form.get('username')

        #check if pk is not in the database
        if does_student_exist(id): 
            print("back")
            return redirect(url_for('dashboard', name=id, back=True))
        
        else: 
            print("new")
            add_student(id, "test")
            return redirect(url_for('dashboard', name=id, back=False))
        


#restricted (jk its not)
@app.route('/dashboard')
def dashboard():
    back = request.args.get("back") == "True"

    return render_template('dashboard.html', name=request.args.get("name"), back=back)
   

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=8000, debug=True)

