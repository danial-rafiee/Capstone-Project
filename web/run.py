from flask import Flask,render_template

app = Flask(__name__)

@app.route("/")
def home():
    energy =120
    return render_template("dashboard.html", energy =energy)

if __name__ == "__main__":
    app.run(debug=True)