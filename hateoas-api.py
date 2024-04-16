
from flask import request
from flask import render_template_string
from flask import Flask
from flask import redirect
from flask import url_for
from flask_cors import CORS

app = Flask(__name__)
app.config['Access-Control-Allow-Origin'] = '*'
CORS(app)

@app.route("/")
def index():
    return render_template_string("""
        {% extends "base.html" %}
        {% block body %}
        <main>
            <h1>Home</h1>
        </main>
        {% endblock %}
    """)

def main():
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=True)

if __name__ == "__main__":
    main()
