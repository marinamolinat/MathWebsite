from flask import Flask, render_template, request, sessions
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



app = Flask(__name__)
app.secret_key = "will change this later lol"


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def login():
    myname = request.args.get('name')
    if myname is None:
        myname = "Guest"
    
    return render_template('login.html', name=myname)


#restricted (jk its not)
@app.route('/secret', methods=['POST'])
def secret ():
    name = request.form.get('username', "idk")
    password = request.form.get('password', "idk")
    return render_template('secret.html', name=name, password=password)

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=8000, debug=True)

