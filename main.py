from flask import Flask, render_template, request

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    myname = request.args.get('name')
    if myname is None:
        myname = "Guest"
    
    return render_template('login.html', name=myname)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)

