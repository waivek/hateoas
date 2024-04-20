
from flask import request
from flask import render_template_string
from flask import render_template
from flask import Flask
from flask import redirect
from flask import url_for
from flask_cors import CORS
from dbutils import Connection
from dataclasses import dataclass

app = Flask(__name__)
app.config['Access-Control-Allow-Origin'] = '*'
CORS(app)

connection = Connection('data/main.db')
videos_connection = Connection('data/videos.db')

@dataclass
class Sequence:
    id: int
    name: str
    description: str
    def __getitem__(self, key):
        return getattr(self, key)

@dataclass
class Portion:
    id: int
    sequence_id: int
    title: str
    epoch: int
    duration: int
    user_id: int
    order: int
    def __getitem__(self, key):
        return getattr(self, key)

@dataclass
class PortionUrl:
    id: int
    portion_id: int
    url: str
    selected: bool
    user_id: int
    def __getitem__(self, key):
        return getattr(self, key)

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

def urls_to_videos(urls):
    video_ids = [ url.replace("https://www.youtube.com/watch?v=", "").replace("https://www.twitch.tv/videos/", "") for url in urls ]
    cursor = videos_connection.cursor()
    cursor.execute("SELECT * FROM videos WHERE id IN ({})".format(",".join(["?" for _ in video_ids])), video_ids)
    return [dict(video) for video in cursor.fetchall()]

def portion_ids_to_videos(portion_ids):
    assert type(portion_ids) == list, f"[portion_ids_to_videos] portion_ids must be a list, got {type(portion_ids)}"
    cursor = connection.cursor()
    video_cursor = videos_connection.cursor()
    videos = []

    for portion_id in portion_ids:
        cursor.execute("SELECT user_id FROM portions WHERE id = ?", (portion_id,))
        user_id = cursor.fetchone()[0]

        cursor.execute("SELECT url FROM portionurls WHERE portion_id = ?", (portion_id,))
        urls = [portionurl["url"] for portionurl in cursor.fetchall()]
        video_ids = [ url.replace("https://www.youtube.com/watch?v=", "").replace("https://www.twitch.tv/videos/", "") for url in urls ]

        video_cursor.execute("SELECT * FROM videos WHERE id IN ({}) AND user_id == ?".format(",".join(["?" for _ in video_ids])), video_ids + [user_id])
        rows = video_cursor.fetchall()
        assert len(rows) == 1, f"[portion_ids_to_videos] expected 1 video, got {len(rows)}"
        videos.append(dict(rows[0]))

    return videos

@app.route("/sequences/<int:sequence_id>/portions/<int:portion_id>/portionurls/<int:portionurl_id>/unselect", methods=["POST"])
def unselect_portionurl(sequence_id, portion_id, portionurl_id):
    with connection:
        connection.execute("UPDATE portionurls SET selected = 0 WHERE id = ?", (portionurl_id,))
    return redirect(url_for("view_portion", sequence_id=sequence_id, portion_id=portion_id))

@app.route("/sequences/<int:sequence_id>/portions/<int:portion_id>/portionurls/<int:portionurl_id>/select", methods=["POST"])
def select_portionurl(sequence_id, portion_id, portionurl_id):
    with connection:
        connection.execute("UPDATE portionurls SET selected = 1 WHERE id = ?", (portionurl_id,))
    return redirect(url_for("view_portion", sequence_id=sequence_id, portion_id=portion_id))

@app.route("/sequences/<int:sequence_id>/portions/<int:portion_id>/view", methods=["GET"])
def view_portion(sequence_id, portion_id):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM portions WHERE id = ?", (portion_id,))
    portion = Portion(**cursor.fetchone())
    # portion_user_name = videos_connection.execute("SELECT user_name FROM videos WHERE user_id = ?", (portion["user_id"],)).fetchone()[0]
    portion_video = portion_ids_to_videos([portion_id])[0]
    cursor.execute("SELECT * FROM portionurls WHERE portion_id = ?", (portion_id,))
    portionurls = [PortionUrl(**portionurl) for portionurl in cursor.fetchall()]
    
    videos = urls_to_videos([url["url"] for url in portionurls])
    extras = []
    for video in videos:
        D = {}
        D["user_id"] = video["user_id"]
        D["user_name"] = video["user_name"]
        D["offset"] = portion["epoch"] - video["created_at_epoch"]
        extras.append(D)

    # reorder extras and portionurls so that the original video is first
    original_index = next(i for i, extra in enumerate(extras) if extra["user_id"] == portion["user_id"])
    extras = [extras[original_index]] + extras[:original_index] + extras[original_index+1:]
    portionurls = [portionurls[original_index]] + portionurls[:original_index] + portionurls[original_index+1:]

    # offset = portion["epoch"] - portion_video["created_at_epoch"]
    # offset_hhmmss = hhmmss(offset)
    # return offset_hhmmss

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}View Portion{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>View Portion</h1>
        {% include "nav.html" %}
        <div>
            <a href="{{ url_for('view_portions', id=portion['sequence_id']) }}">Back to Portions</a>
        </div>
        <div class="box tall">
            <div>Portion by: {{ portion_video["user_name"] }}, created {{ portion['epoch'] | timeago }}, with a duration of: {{ portion['duration'] | hhmmss }} on video: {{ portion_video['id'] }} offset: {{ (portion['epoch'] - portion_video['created_at_epoch']) | hhmmss   }}</div>
            <div>{{ portion['title'] }}</div>
            <div>{{ portion }}</div>
        </div>
        <h3>Selected URLs</h3>
        {% for extra, portionurl in zip(extras, portionurls) if portionurl['selected'] %}
        <div class="box tall">
            <div>Portion URL belongs to user: {{ extra['user_name'] }} on url: {{ portionurl["url"] }} offset: {{ extra['offset'] | hhmmss }}</div>
            {% if portion['user_id'] == extra['user_id'] %}
            <span>Original URL</span>
            {% else %}
            <form action="{{ url_for('unselect_portionurl', sequence_id=portion['sequence_id'], portion_id=portion['id'], portionurl_id=portionurl['id']) }}" method="POST">
                <button type="submit">Unselect</button>
            </form>
            {% endif %}
            <div>{{ portionurl }}</div>
        </div>
        {% endfor %}
        <h3>Unselected URLs</h3>
        {% for extra, portionurl in zip(extras, portionurls) if not portionurl['selected'] %}
        <div class="box tall">
            <div>Portion URL belongs to user: {{ extra['user_name'] }} on video: {{ extra['user_id'] }} offset: {{ extra['offset'] | hhmmss }}</div>
            <form action="{{ url_for('select_portionurl', sequence_id=portion['sequence_id'], portion_id=portion['id'], portionurl_id=portionurl['id']) }}" method="POST">
                <button type="submit">Select</button>
            </form>
            <div>{{ portionurl }}</div>
        </div>
        {% endfor %}

    </main>
    {% endblock %}""", portion=portion, portionurls=portionurls, extras=extras, zip=zip, portion_video=portion_video)


@app.route("/sequences/<int:id>/view")
def view_portions(id):
    portions = []
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM sequences WHERE id = ?", (id,))
    sequence = Sequence(**cursor.fetchone())
    cursor.execute("SELECT * FROM portions WHERE sequence_id = ?", (id,))
    portions = [Portion(**portion) for portion in cursor.fetchall()]

    extras = []
    for portion in portions:
        D = {}
        cursor = connection.execute("SELECT * FROM portionurls WHERE portion_id = ?", (portion["id"],))
        D["portionurls"] = [PortionUrl(**url) for url in cursor.fetchall()]
        
        
        videos = urls_to_videos([portionurl["url"] for portionurl in D["portionurls"]])
        video = next(video for video in videos if video["user_id"] == portion["user_id"])
        
        D["video"] = video
        D["offset"] = portion["epoch"] - video["created_at_epoch"]
        extras.append(D)

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}View Sequence {{ sequence['name'] }} / View Portions{% endblock %}
    {% block body %}
    <main class="mono tall">
        
        <h1>View Sequence {{ sequence['name'] }} / View Portions</h1>
        <h3>Portions</h3>
        {% include "nav.html" %}
        {% for extra, portion in zip(extras, portions) %}
        <div class="box tall">
            <div><a href="{{ url_for('view_portion', sequence_id=sequence['id'], portion_id=portion['id']) }}">View Portion with {{ extra['portionurls'] | length }} URL{{ 's' if extra['portionurls'] | length != 1 else '' }}</a></div>
            <div>Portion by: {{ extra['video']['user_name'] }}, created {{ extra['video']['created_at_epoch'] | timeago }}, with a duration of: {{ portion['duration'] | hhmmss }} on video: {{ extra['video']['id'] }} offset: {{ extra['offset'] }}</div>
            <div>{{ portion['title'] }}</div>
            <form action="{{ url_for('delete_portion', portion_id=portion['id']) }}" method="GET">
                <button type="submit">Delete</button>
            </form>
            <div>{{ portion }}</div>
        </div>
        {% endfor %}
        {% if not portions %}
        <div class="box">
            No portions found
        </div>
        {% endif %}
    </main>
    {% endblock %}""", portions=portions, sequence=sequence, extras=extras, zip=zip)


@app.route("/sequences/view")
def view_sequences():
    sequences = []
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM sequences")
    sequences = [Sequence(**seq) for seq in cursor.fetchall()]

    # get portion-count of each sequence
    extras = []
    for seq in sequences:
        D = {}
        cursor.execute("SELECT COUNT(*) FROM portions WHERE sequence_id = ?", (seq["id"],))
        D["portion_count"] = cursor.fetchone()[0]
        extras.append(D)




    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}View Sequences{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>View Sequences</h1>
        {% include "nav.html" %}
        {% for seq, extra in zip(sequences, extras) %}
        <div class="box tall">
            <div class="tall">
                <a href="{{ url_for('view_portions', id=seq['id']) }}">View {{ extra['portion_count'] }} Portion{{ 's' if extra['portion_count'] != 1 else '' }} of {{ seq['name'] }}</a>
            </div>
            <div>{{ seq }}</div>
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
    {% endblock %}""", sequences=sequences, extras=extras, zip=zip)


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

def get_synced_videos(video_id, offset):
    cursor = videos_connection.cursor()
    cursor.execute("SELECT created_at_epoch + ? AS epoch, user_id FROM videos WHERE id = ?", (offset, video_id))
    epoch, user_id = cursor.fetchone()
    cursor.execute("SELECT * FROM videos WHERE ? BETWEEN created_at_epoch AND created_at_epoch + duration AND user_id != ?", (epoch, user_id))
    return [dict(video) for video in cursor.fetchall()]



@app.route("/portions/<portion_id>/delete", methods=["GET"])
def delete_portion(portion_id):
    cursor = connection.cursor()
    cursor.execute("SELECT sequence_id FROM portions WHERE id = ?", (portion_id,))
    sequence_id = cursor.fetchone()[0]
    cursor.execute("DELETE FROM portions WHERE id = ?", (portion_id,))
    connection.commit()
    return redirect(url_for("view_portions", id=sequence_id))

@app.route("/sequences/<sequence_id>/portions", methods=["POST"])
def create_portion(sequence_id):
    start = int(request.form["start"])

    title = request.form["title"]
    duration = int(request.form["end"])-start
    epoch = int(request.form["created_at_epoch"]) + start
    order = connection.execute("SELECT COALESCE(MAX(`order`), 0) + 1 FROM portions WHERE sequence_id = ?", (sequence_id,)).fetchone()[0]

    cursor = connection.cursor()
    # insert (sequence_id, title, epoch, duration, user_id, order)
    cursor.execute("INSERT INTO portions (sequence_id, title, epoch, duration, user_id, `order`) VALUES (?, ?, ?, ?, ?, ?)", (sequence_id, title, epoch, duration, request.form["user_id"], order))
    portion_id = cursor.lastrowid

    videos_cursor = videos_connection.execute("SELECT user_id FROM videos WHERE url = ?", (request.form["url"],))
    user_id = videos_cursor.fetchone()[0]

    # portionurls(portion_id, url, original, selected)
    cursor = connection.cursor()
    cursor.execute("INSERT INTO portionurls (portion_id, url, selected, user_id) VALUES (?, ?, ?)", (portion_id, request.form["url"], True, user_id))
    cursor = connection.cursor()
    videos = get_synced_videos(request.form["video_id"], start)
    portionurls = [(portion_id, video["url"], False, video["user_id"]) for video in videos]
    cursor.executemany("INSERT INTO portionurls (portion_id, url, selected) VALUES (?, ?, ?)", portionurls)
    connection.commit()
    return redirect(url_for("view_portions", id=sequence_id))



@app.route("/form_create_portion", methods=["GET"])
def form_create_portion():
    sequence_id = request.args.get("sequence_id")
    video_id = request.args.get("video_id")
    cursor = videos_connection.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    video = dict(cursor.fetchone())
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Create Portion{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Create Portion</h1>
        {% include "nav.html" %}
        <div class="box tall">
            <h3>Create Portion</h3>
            <form action="{{ url_for('create_portion', sequence_id=sequence_id) }}" method="POST" class="tall">
                <div>
                    <!-- portion(sequence_id, title, start, end, user_id -->
                    <!-- readonly: sequence_id, user_id -->
                    <!-- required: all -->
                    <label>sequence_id</label>
                    <input name="sequence_id" value="{{ sequence_id }}" readonly>

                    <label>user_id</label>
                    <input name="user_id" value="{{ video['user_id'] }}" readonly>

                    <label>created_at_epoch</label>
                    <input name="created_at_epoch" value="{{ video['created_at_epoch'] }}" readonly>

                    <label>url</label>
                    <input name="url" value="{{ video['url'] }}" readonly>

                    <label>video_id</label>
                    <input name="video_id" value="{{ video['id'] }}" readonly>

                </div>

                <div>
                    <input type="text" name="title" placeholder="title" value="{{ video['title'] }}" required>
                    <input type="text" name="start" placeholder="start" required>
                    <input type="text" name="end" placeholder="end" required>
                </div>
                <div>
                    <button type="submit">Create</button>
                </div>
            </form>
        </div>
    </main>
    {% endblock %}""", sequence_id=sequence_id, video=video)

@app.route("/videos/<id>")
def video(id):
    cursor = connection.execute("SELECT * FROM sequences")
    sequences = [ Sequence(**seq) for seq in cursor.fetchall() ]


    cursor = videos_connection.cursor()
    cursor.execute("SELECT * FROM videos WHERE id = ?", (id,))
    video = dict(cursor.fetchone())
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Video{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Video</h1>
        {% include "nav.html" %}
        <div class="box tall">
            <div>Video by: {{ video['user_name'] }}, created {{ video['created_at_epoch'] | timeago }}, with a duration of: {{ video['duration'] | hhmmss }}</div>
            <div>{{ video['title'] }}</div>
            <div>{{ video }}</div>
        </div>
        <div class="box tall">
            <!-- dynamic form for create_portion where sequence_id is selected via dropdown -->
            {% for sequence in sequences %}
            <div><a href="{{ url_for('form_create_portion', sequence_id=sequence['id'], video_id=video['id']) }}">Add to {{ sequence['name'] }}</a></div>
            {% endfor %}
        </div>
    </main>
    {% endblock %}""", video=video, sequences=sequences)


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
    conditions = []
    parameters = []
    if start_date:
        conditions.append("created_at_epoch >= ?")
        parameters.append(start_date)
    if end_date:
        conditions.append("created_at_epoch <= ?")
        parameters.append(end_date)
    if user_id:
        conditions.append("user_id = ?")
        parameters.append(user_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at_epoch DESC"
    query += " LIMIT ? OFFSET ?"
    parameters.extend([limit, offset])
    cursor.execute(query, parameters)

    videos = [dict(video) for video in cursor.fetchall()]

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
            <div><a href="{{ url_for('video', id=video['id']) }}">View</a></div>
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



@app.route("/downloads")
def downloads():
    cursor = connection.execute("SELECT * FROM sequences")
    sequences = [ dict(seq) for seq in cursor.fetchall() ]
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Downloads{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Downloads</h1>
        {% include "nav.html" %}
        {% for sequence in sequences %}
        <div class="box tall">
            <div>{{ sequence['name'] }}</div>
            <div><a href="">Download {{ sequence['name'] }}</a></div>
            <div><a href="{{ url_for('view_portions', id=sequence['id']) }}">View Portions of {{ sequence['name'] }}</a></div>
        </div>
        {% endfor %}
    </main>
    {% endblock %}""", sequences=sequences)

def main():
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=True)

if __name__ == "__main__":
    main()
