
from flask import request
from flask import render_template_string
from flask import render_template
from flask import Flask
from flask import redirect
from flask import url_for
from flask_cors import CORS
from dbutils import Connection

app = Flask(__name__)
app.config['Access-Control-Allow-Origin'] = '*'
CORS(app)

connection = Connection('data/main.db')
    


@app.route("/elements")
def elements():
    return render_template("elements.html")

# @app.template_filter()
# def html_list(items):
#     return render_template_string("""
#         <div class="tall">
#             {% for item in items %}
#             <div class="box">
#                 <pre>{{ item }}</pre>
#             </div>
#             {% endfor %}
#         </div>""", items=items)

@app.route("/sequences/<int:id>/delete", methods=["GET"])
def delete_sequence(id):
    cursor = connection.cursor()
    cursor.execute("DELETE FROM sequences WHERE id = ?", (id,))
    connection.commit()
    return redirect(url_for("view_sequences"))

@app.route("/sequences", methods=["POST"])
def create_sequence():
    name = request.form.get("name")
    description = request.form.get("description")
    cursor = connection.cursor()
    cursor.execute("INSERT INTO sequences (name, description) VALUES (?, ?)", (name, description))
    connection.commit()
    return redirect(url_for("view_sequences"))

@app.route("/sequences/<int:id>/view_portions")
def view_portions(id):
    portions = []
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM portions WHERE sequence_id = ?", (id,))
    portions = [dict(portion) for portion in cursor.fetchall()]
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}View Portions{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>View Portions</h1>
        {% include "nav.html" %}
        {% for portion in portions %}
        <div class="box tall">
            <pre>{{ portion }}</pre>
        </div>
        {% endfor %}
        {% if not portions %}
        <div class="box">
            No portions found
        </div>
        {% endif %}
    </main>
    {% endblock %}""", portions=portions)

@app.route("/view_sequences")
def view_sequences():
    sequences = []
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM sequences")
    sequences = [dict(seq) for seq in cursor.fetchall()]


    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}View Sequences{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>View Sequences</h1>
        {% include "nav.html" %}
        {% for seq in sequences %}
        <div class="box tall">
            <div class="tall">
                <a href="{{ url_for('view_portions', id=seq['id']) }}">View Portions</a>
            </div>
            <pre>{{ seq }}</pre>
            <div class="wide">
                <form action="{{ url_for('delete_sequence', id=seq['id']) }}" method="DELETE">
                    <button type="submit">Delete</button>
                </form>
            </div>
        </div>
        {% endfor %}
        {% if not sequences %}
        <div class="box">
            No sequences found
        </div>
        {% endif %}
        <div class="box tall">
            <h3>Create Sequence</h3>
            <form action="{{ url_for('create_sequence') }}" method="POST" class="tall">
                <div>
                    <input type="text" name="name" placeholder="name">
                    <input type="text" name="description" placeholder="Description">
                </div>
                <div>
                    <button type="submit">Create</button>
                </div>
            </form>
        </div>
    </main>
    {% endblock %}""", sequences=sequences)

@app.route("/")
def home():
    with connection:
        list_of_tables_to_select_1_from = [ 'sequences', 'portions', 'portionurls' ]
        for table in list_of_tables_to_select_1_from:
            connection.execute(f"SELECT 1 FROM {table}")
    return render_template_string("""
        {% extends "base.html" %}
        {% block title %}Home{% endblock %}
        {% block body %}
        <main class="mono tall">
            <h1>Home</h1>
            {% include "nav.html" %}
        </main>
        {% endblock %}
    """)

def main():
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=True)

if __name__ == "__main__":
    main()
