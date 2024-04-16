
from flask import request
from flask import render_template_string
from flask import render_template
from flask import Flask
from flask import redirect
from flask import url_for
from flask_cors import CORS

app = Flask(__name__)
app.config['Access-Control-Allow-Origin'] = '*'
CORS(app)

@app.route("/elements")
def elements():
    return render_template("elements.html")

@app.route("/")
def index():
    return render_template_string("""
        {% extends "base.html" %}
        {% block title %}Home{% endblock %}
        {% block body %}
        <main class="mono tall">
            <h1>Home</h1>
            <div class="wide">
                <a href="{{ url_for('elements') }}">Elements</a>
            </div>
        </main>
        {% endblock %}
    """)

def main():
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=True)

if __name__ == "__main__":
    main()
