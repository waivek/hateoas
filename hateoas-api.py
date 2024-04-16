
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
videos_connection = Connection('data/videos.db')
    
# register global filter
@app.template_filter('timeago')
def timeago(value):
    import timeago
    return timeago.format(value)

@app.template_filter('hhmmss')
def hhmmss(value):
    from waivek import Timestamp
    timestamp = Timestamp(value)
    return timestamp.hh_mm_ss


@app.route("/elements")
def elements():
    return render_template("elements.html")

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

@app.route("/videos")
def videos():
    start_date = request.args.get("start_date", None)
    end_date = request.args.get("end_date", None)
    user_id = request.args.get("user_id", None)
    page = int(request.args.get("page", 1))
    cursor = videos_connection.cursor()
    limit = 10
    offset = (page - 1) * limit

    query = "SELECT * FROM videos"
    if start_date:
        query += " WHERE created_at_epoch >= ?"
    if end_date:
        query += " WHERE created_at_epoch <= ?"
    if user_id:
        query += " WHERE user_id = ?"
    query += " ORDER BY created_at_epoch DESC"
    query += " LIMIT ? OFFSET ?"


    if start_date and end_date and user_id:
        cursor.execute(query, (start_date, end_date, user_id, limit, offset))
    elif start_date and end_date:
        cursor.execute(query, (start_date, end_date, limit, offset))
    elif start_date and user_id:
        cursor.execute(query, (start_date, user_id, limit, offset))
    elif end_date and user_id:
        cursor.execute(query, (end_date, user_id, limit, offset))
    elif start_date:
        cursor.execute(query, (start_date, limit, offset))
    elif end_date:
        cursor.execute(query, (end_date, limit, offset))
    elif user_id:
        cursor.execute(query, (user_id, limit, offset))
    else:
        cursor.execute(query, (limit, offset))

    videos = [dict(video) for video in cursor.fetchall()]

    # pagination: { currentPage, currentPageSize, pageCount, isFirstPage, isLastPage, prev, next }
    # pagination: total

    cursor.execute("SELECT COUNT(*) FROM videos")
    total = cursor.fetchone()[0]
    page_count = total // limit
    if total % limit:
        page_count += 1

    pagination = {
        "currentPage": page,
        "currentPageSize": len(videos),
        "pageCount": page_count,
        "isFirstPage": page == 1,
        "isLastPage": page == page_count,
        "prev": page - 1 if page > 1 else None,
        "next": page + 1 if page < page_count else None,
        "total": total
    }




    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Videos{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Videos</h1>
        {% include "nav.html" %}
        <!-- pagination controls -->
        <div class="box tall">
            <h3>Pagination</h3>
            <div>
                <form action="{{ url_for('videos') }}" method="GET">
                    <input type="text" name="start_date" placeholder="start_date">
                    <input type="text" name="end_date" placeholder="end_date">
                    <input type="text" name="user_id" placeholder="user_id">
                    <button type="submit">Filter</button>
                </form>
            </div>
            <div>
                {% if pagination['isFirstPage'] %}
                <span class="gray">First</span>
                {% else %}
                <a href="{{ url_for('videos', page=1) }}">First</a>
                {% endif %}
                {% if pagination['prev'] %}
                <a href="{{ url_for('videos', page=pagination['prev']) }}">Prev</a>
                {% else %}
                <span class="gray">Prev</span>
                {% endif %}

                <span>Page {{ pagination['currentPage'] }} of {{ pagination['pageCount'] }}</span>

                {% if pagination['next'] %}
                <a href="{{ url_for('videos', page=pagination['next']) }}">Next</a>
                {% else %}
                <span class="gray">Next</span>
                {% endif %}
                {% if pagination['isLastPage'] %}
                <span class="gray">Last</span>
                {% else %}
                <a href="{{ url_for('videos', page=pagination['pageCount']) }}">Last</a>
                {% endif %}
            </div>
            <div>
                <span>Total: {{ pagination['total'] }}</span>
            </div>
        </div>
        <!-- pagination controls -->


        {% for video in videos %}
        <div class="box tall">
            <div>Video by: {{ video['user_name'] }}, created {{ video['created_at_epoch'] | timeago }}, with a duration of: {{ video['duration'] | hhmmss }}</div>
            <div>{{ video['title'] }}</div>
            <div>{{ video }}</div>
        </div>
        {% endfor %}
        {% if not videos %}
        <div class="box">
            No videos found
        </div>
        {% endif %}
    </main>
    {% endblock %}""", videos=videos, pagination=pagination)






def main():
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=True)

if __name__ == "__main__":
    main()
