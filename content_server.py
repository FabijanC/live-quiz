from flask import Flask

app = Flask(__name__, static_folder="static")
app.config['SECRET_KEY'] = 'secret!'
@app.route("/")
def root():
    return app.send_static_file("index.html")

@app.route("/favicon.ico")
def icon():
    return app.send_static_file("lightbulb.ico")

if __name__ == '__main__':
    app.run()