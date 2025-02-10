
from datetime import datetime, timezone
import time
from zoneinfo import ZoneInfo
from flask import jsonify, request
from flask import render_template_string
from flask import render_template
from flask import Flask
from flask import redirect
from flask import url_for
from flask import session
from flask_cors import CORS
from dbutils import Connection
from Types import Sequence, Portion, PortionUrl
from box import usable
from portionurl_to_download_path import downloaded, partially_downloaded
from worker_utils import get_download_filename, get_graph_payloads_downloads_folder, get_offsets_downloads_folder, has_chat_part_file, is_chat_downloaded, portionurl_id_to_filename
from worker_encode_video import encoded
from worker_crop_video import cropped, in_crop_queue
from typing import TypedDict
from waivek import read, rel2abs, write
import os.path
import socket


app = Flask(__name__)
app.secret_key = 'flash'
app.config['Access-Control-Allow-Origin'] = '*'
# app.jinja_env.globals.update(now=datetime.now)
CORS(app)

connection = Connection('data/main.db')
videos_connection = Connection('data/videos.db')
clips_connection = Connection('data/clips.db')
games_connection = Connection('data/games.db')

def get_history_db_schema() -> str:
    schema_string = """
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        epoch INTEGER,
        method TEXT,
        status_code INTEGER,
        path TEXT
    ) STRICT;
    """
    from textwrap import dedent
    return dedent(schema_string.strip())

def now() -> int:
    non_naive_utc = datetime.now(timezone.utc)
    return int(non_naive_utc.timestamp())

# before-request, log the explicit url path in a text file along with the timestamp
@app.after_request
def log_request(response):
    log_path = rel2abs('data/history.txt')
    epoch = now()
    method = request.method
    # url = request.url
    status_code = response.status_code
    path = request.path
    params = request.args
    full_url = request.full_path
    if full_url.endswith("?"):
        full_url = full_url[:-1]
    with open(log_path, 'a') as f:
        f.write(f'{epoch} {method} {status_code} {full_url}\n')
    connection = Connection("data/hateoas-history.db")
    connection.execute(get_history_db_schema())
    # connection.execute("INSERT INTO history (epoch, method, status_code, path) VALUES (?, ?, ?, ?)", (epoch, method, status_code, path))
    connection.execute("INSERT INTO history (epoch, method, status_code, path) VALUES (?, ?, ?, ?)", (epoch, method, status_code, full_url))
    connection.commit()

    return response



def portionurl_downloaded(portionurl: PortionUrl) -> bool:
    assert app and app.static_folder, "[portionurl_downloaded] app.static_folder is not set"
    static_folder = app.static_folder
    filename = f"{static_folder}/downloads/{portionurl.id}.mp4"
    import os
    return os.path.exists(filename)

def download_hash(portionurl: PortionUrl, portion: Portion, video: dict) -> str:
    offset = portion.epoch - video["created_at_epoch"]
    hash_inputs = [ video['user_name'], video['id'], offset, portion.duration ]
    # import hashlib
    # return hashlib.md5("".join(map(str, hash_inputs)).encode()).hexdigest()
    return ",".join(map(str, hash_inputs))

td = TypedDict("td", {"user_name": str, "url": str, "offset": int, "duration": int, "filename": str, "hash": str})
def format_portionurl_for_download(portionurl: PortionUrl, portion: Portion) -> td:
    # format to return { user_name, url, offset, duration }
    video_id = portionurl.url.replace("https://www.youtube.com/watch?v=", "").replace("https://www.twitch.tv/videos/", "")
    cursor = videos_connection.cursor()
    cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    video = dict(cursor.fetchone())
    user_name = video["user_name"]
    offset = portion.epoch - video["created_at_epoch"]

    return {
        "user_name": user_name,
        "url": portionurl.url,
        "offset": offset,
        "duration": portion.duration,
        "filename": get_download_filename(portionurl, portion, video),
        "hash": download_hash(portionurl, portion, video)
    }

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

@app.template_filter('abbreviate')
def abbreviate(value):
    from waivek.print_utils import abbreviate
    return abbreviate(value)

@app.template_filter('to_ist')
def to_ist(epoch):
    dt = datetime.fromtimestamp(epoch).astimezone(ZoneInfo("Asia/Kolkata"))
    return dt.strftime("%a %b %e %I:%M%p %z")


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
    # assert type(portion_ids) == list, f"[portion_ids_to_videos] portion_ids must be a list, got {type(portion_ids)}"
    assert isinstance(portion_ids, list), f"[portion_ids_to_videos] portion_ids must be a list, got {type(portion_ids)}"
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
        connection.execute("INSERT INTO downloads (portionurl_id, status) VALUES (?, 'paused')", (portionurl_id,))


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
        <div class="wide">
            <a href="{{ url_for('view_portions', id=portion['sequence_id']) }}">Back to Portions</a>
            <a href="{{ url_for('downloads_sequence', sequence_id=portion['sequence_id']) }}">{{ url_for('downloads_sequence', sequence_id=portion['sequence_id']) }}</a>
        </div>
        <div class="box tall">
            <div>Portion by: {{ portion_video["user_name"] }}, created {{ portion['epoch'] | timeago }}, with a duration of: {{ portion['duration'] | hhmmss }} on video: {{ portion_video['id'] }} offset: {{ (portion['epoch'] - portion_video['created_at_epoch']) | hhmmss   }}</div>
            <!-- <div>{{ portion['title'] }}</div> -->
            <!-- do above but with form to update title -->
            <form action="{{ url_for('update_portion', portion_id=portion['id']) }}" method="POST" class="tall">
                <input type="text" name="title" value="{{ portion['title'] }}">
                <div><button type="submit">Update Title</button></div>
            </form>

            <div>{{ portion }}</div>
        </div>
        <div class="tall">
            <div class="tall">
                <h3>Selected URLs</h3>
                <div class="wide">
                {% for extra, portionurl in zip(extras, portionurls) if portionurl['selected'] %}
                    <div class="box tall">
                        <div title="{{ portionurl["url"] }} @ {{ extra['offset'] | hhmmss }}">{{ extra['user_name'] }}</div>
                        {% if portion['user_id'] == extra['user_id'] %}
                        <span>Original URL</span>
                        {% else %}
                        <form action="{{ url_for('unselect_portionurl', sequence_id=portion['sequence_id'], portion_id=portion['id'], portionurl_id=portionurl['id']) }}" method="POST">
                            <button type="submit">Unselect</button>
                        </form>
                        {% endif %}
                    </div>
                {% endfor %}
                </div>
            </div>
            <div class="tall">
                <h3>Unselected URLs</h3>
                <div class="wide">
                {% for extra, portionurl in zip(extras, portionurls) if not portionurl['selected'] %}
                    <div class="box tall">
                        <div title="{{ portionurl["url"] }} @ {{ extra['offset'] | hhmmss }}">{{ extra['user_name'] }}</div>
                        <form action="{{ url_for('select_portionurl', sequence_id=portion['sequence_id'], portion_id=portion['id'], portionurl_id=portionurl['id']) }}" method="POST">
                            <div class="tall">
                                {# add a toggle for resync #}
                                <div class="wide">
                                    <input type="checkbox" name="resync" value="true">
                                    <label for="resync">Resync</label>
                                </div>
                                <button type="submit">Select</button>
                            </div>
                        </form>
                    </div>
                {% endfor %}
                </div>
            </div>
        </div>

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
        try:
            video = next(video for video in videos if video["user_id"] == portion["user_id"])
        except StopIteration as stop_iteration_error:
            print(portion.pretty())
            raise stop_iteration_error
        
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
            <div>
                <a href="{{ url_for('view_portion', sequence_id=sequence['id'], portion_id=portion['id']) }}">{{ url_for('view_portion', sequence_id=sequence['id'], portion_id=portion['id']) }}</a>
                <span class="gray font-bold">({{ extra['portionurls'] | length }} URL{{ 's' if extra['portionurls'] | length != 1 else '' }})</span>
            </div>
            <div>Portion by: {{ extra['video']['user_name'] }}, created {{ extra['video']['created_at_epoch'] | timeago }}, with a duration of: {{ portion['duration'] | hhmmss }} on video: {{ extra['video']['id'] }} offset: {{ extra['offset'] }}</div>
            <!-- <div>{{ portion['title'] }}</div> -->
            <form action="{{ url_for('update_portion', portion_id=portion['id']) }}" method="POST" class="tall">
                <input type="text" name="title" value="{{ portion['title'] }}">
                <div><button type="submit">Update Title</button></div>
            </form>
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


def get_synced_videos(video_id, offset):
    cursor = videos_connection.execute("SELECT created_at_epoch + ? AS epoch, user_id FROM videos WHERE id = ?", (offset, video_id))
    epoch, user_id = cursor.fetchone()
    cursor.execute("SELECT * FROM videos WHERE ? BETWEEN created_at_epoch AND created_at_epoch + duration AND user_id != ?", (epoch, user_id))
    return [dict(video) for video in cursor.fetchall()]

@app.route("/portions/<portion_id>", methods=["POST"])
def update_portion(portion_id):
    title = request.form["title"]
    cursor = connection.cursor()
    cursor.execute("UPDATE portions SET title = ? WHERE id = ?", (title, portion_id))
    connection.commit()
    return redirect(request.referrer)

@app.route("/portions/<portion_id>/delete", methods=["GET"])
def delete_portion(portion_id):
    cursor = connection.cursor()

    # get portion_order
    cursor.execute("SELECT `order` FROM portions WHERE id = ?", (portion_id,))
    portion_order = cursor.fetchone()[0]

    cursor.execute("SELECT sequence_id FROM portions WHERE id = ?", (portion_id,))
    sequence_id = cursor.fetchone()[0]
    cursor.execute("DELETE FROM portions WHERE id = ?", (portion_id,))

    # ensure correct order is maintained after `portion_order` is removed
    cursor.execute("UPDATE portions SET `order` = `order` - 1 WHERE sequence_id = ? AND `order` > ?", (sequence_id, portion_order))

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
    cursor.execute("INSERT INTO portionurls (portion_id, url, selected, resync, user_id) VALUES (?, ?, ?, ?, ?)", (portion_id, request.form["url"], True, False, user_id))
    cursor.execute("INSERT INTO downloads (portionurl_id, status) VALUES (?, 'paused')", (cursor.lastrowid,))

    cursor = connection.cursor()
    videos = get_synced_videos(request.form["video_id"], start)
    portionurls = [(portion_id, video["url"], False, False, video["user_id"]) for video in videos]
    cursor.executemany("INSERT INTO portionurls (portion_id, url, selected, resync, user_id) VALUES (?, ?, ?, ?, ?)", portionurls)

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
                    <input type="text" name="sequence_id" value="{{ sequence_id }}" readonly>

                    <label>user_id</label>
                    <input type="text" name="user_id" value="{{ video['user_id'] }}" readonly>

                    <label>created_at_epoch</label>
                    <input type="text" name="created_at_epoch" value="{{ video['created_at_epoch'] }}" readonly>

                    <label>url</label>
                    <input type="text" name="url" value="{{ video['url'] }}" readonly>

                    <label>video_id</label>
                    <input type="text" name="video_id" value="{{ video['id'] }}" readonly>

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

@app.route("/users_links_html/<user_id>")
def users_links_html(user_id):
    url = request.path
    cursor = videos_connection.execute("SELECT user_id, user_name FROM videos WHERE user_id = ? LIMIT 1;", (user_id,))
    user = dict(cursor.fetchone())
    return render_template_string("""
    <div class="box wide">
        <div>{{ user['user_name'] }}</div>
        <div>{{ user['user_id'] }}</div>

        {% if url.startswith("/videos") %}
        <span class="font-bold">Videos</span>
        {% else %}
        <a href="{{ url_for('videos', user_id=user['user_id']) }}">Videos</a>
        {% endif %}

        {% if url.startswith("/clips") %}
        <span class="font-bold">Clips</span>
        {% else %}
        <a href="{{ url_for('clips', user_id=user['user_id']) }}">Clips</a>
        {% endif %}
    </div>""", user=user, url=url)

@app.route("/videos/<id>")
def video(id):
    cursor = connection.execute("SELECT * FROM sequences")
    sequences = [ Sequence(**seq) for seq in cursor.fetchall() ]


    cursor = videos_connection.cursor()
    cursor.execute("SELECT * FROM videos WHERE id = ?", (id,))
    video = dict(cursor.fetchone())
    thumbnail_url = video["thumbnail_url"].replace("%{width}", "640").replace("%{height}", "360")
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Video{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Video</h1>
        {% include "nav.html" %}
        <div class="box tall">
            <div class="tall">
                <div class="wide">
                    Sync to:
                    <div class="wide separated">
                        {% for sequence in sequences %}
                        <div><a href="{{ url_for('sync_video_to_video', video_id=video['id'], sequence_id=sequence['id']) }}">{{ sequence['name'] }}</a></div>
                        {% endfor %}
                    </div>
                </div>
                {% if not sequences %}
                <div>No sequences found, so we cannot create a portion</div>
                <div><a href="{{ url_for('view_sequences') }}">Create a sequence</a></div>
                {% endif %}
            </div>
            <div>Video by: {{ video['user_name'] }}, created {{ video['created_at_epoch'] | timeago }}, with a duration of: {{ video['duration'] | hhmmss }}</div>
            <div><a href="{{ video['url'] }}">{{ video['url'] }}</a></div>
            <div>{{ video['title'] }}</div>
            <div>
                <img src="{{ thumbnail_url }}" alt="{{ video['title'] }}">
            </div>
            <div>{{ video }}</div>
        </div>
    </main>
    {% endblock %}""", video=video, sequences=sequences, thumbnail_url=thumbnail_url)


@app.route("/videos")
def videos():
    # check if `videos` table exists. if it doesn’t return early with a HTML error message
    cursor = videos_connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos'")
    if not cursor.fetchone():
        return render_template_string("""
        {% extends "base.html" %}
        {% block title %}Videos{% endblock %}
        {% block body %}
        <main class="mono tall">
            <h1>Video</h1>
            {% include "nav.html" %}
            <div class="box tall">
                <div class="error">Table `videos` not found in `videos.db`</div>
            </div>
        </main>
        {% endblock %}""")
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

    links_html = None
    if user_id:
        links_html = users_links_html(user_id)

    cursor = connection.execute("SELECT * FROM sequences")
    sequences = [ Sequence(**seq) for seq in cursor.fetchall() ]

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Videos{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Videos</h1>
        {% include "nav.html" %}

        {% if links_html %}
        {{ links_html | safe }}
        {% endif %}

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
            <div class="tall">
                <div><a href="{{ url_for('video', id=video['id']) }}">View</a></div>
                <div class="wide">
                    Sync to:
                    <div class="wide separated">
                        {% for sequence in sequences %}
                        <div><a href="{{ url_for('sync_video_to_video', video_id=video['id'], sequence_id=sequence['id']) }}">{{ sequence['name'] }}</a></div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            <div>Video by: {{ video['user_name'] }}, created {{ video['created_at_epoch'] | timeago }}, with a duration of: {{ video['duration'] | hhmmss }}</div>
            <div>{{ video['title'] }}</div>
            <div>
                <a href="{{ video['thumbnail_url'].replace('%{width}', '640').replace('%{height}', '360') }}">
                    <img height=150 src="{{ video['thumbnail_url'].replace('%{width}', '640').replace('%{height}', '360') }}" alt="{{ video['title'] }}">
                </a>
            </div>
            <div>{{ video }}</div>
        </div>
        {% endfor %}
        {% if not videos %}
        <div class="box">
            No videos found
        </div>
        {% endif %}
    </main>
    {% endblock %}""", videos=videos, pagination=pagination, sequences=sequences, links_html=links_html)

@app.route("/chat_downloads")
def chat_downloads():
    from get_worker_info import get_chat_worker_info
    from chat_part_file_utils import video_id_to_pct
    cursor = connection.execute("SELECT id, video_id FROM queue_chat")
    queue_chat = [dict(row) for row in cursor.fetchall()]
    worker_table = get_chat_worker_info()
    localtime_hhmmss = datetime.now().strftime("%H:%M:%S")
    
    # query videos from videos.db
    cursor = videos_connection.execute("SELECT * FROM videos WHERE id IN ({})".format(",".join([str(row['video_id']) for row in queue_chat])))
    videos = [dict(row) for row in cursor.fetchall()]
    video_id_to_video = { video['id']: video for video in videos }

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Chat Downloads{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Chat Downloads</h1>
        {% include "nav.html" %}
        <div class="box tall">

            <div>
                The localtime is: {{ localtime_hhmmss }}
            </div>
            {% for worker in worker_table %}
                {% if worker.lock_status == 'stale' %}
                <div>
                    <span class="red">{{ worker.lock_status }}</span>  - {{ worker.lock_filename }} ({{ worker.pid }}) (lock_file exists but PID doesn’t)
                </div>
                {% else %}
                <div>
                    <span class="green">{{ worker.lock_status }}</span>  - {{ worker.lock_filename }} ({{ worker.pid }})
                </div>
                {% endif %}
            {% endfor %}
            {% if worker_table | length == 0 %}
            <div class="error">No workers found</div>
            {% endif %}
            <ol>
                {% for row in queue_chat %}
                <li>
                    <div>
                        <div>
                            <a href="{{ url_for('video', id=row['video_id']) }}">{{ row['video_id'] }}</a>
                        </div>
                        {% set video = video_id_to_video[row['video_id']] %}
                        <div>Video by: {{ video['user_name'] }}, created {{ video['created_at_epoch'] | timeago }}, with a duration of: {{ video['duration'] | hhmmss }}</div>
                    </div>
                    <div>
                        Status:
                        {% if is_chat_downloaded(row['video_id']) %}
                        <span class="green">complete</span>
                        {% elif has_chat_part_file(row['video_id']) %}
                        <span class="yellow">
                            downloading - {{ "%0.2f" | format(video_id_to_pct(row['video_id']) ) }}%
                        </span>
                        {% else %}
                        <span class="red">pending</span>
                        {% endif %}
                    </div>
                </li>
                {% endfor %}
            </ol>
        </div>
    </main>
    {% endblock %}""", queue_chat=queue_chat, worker_table=worker_table, is_chat_downloaded=is_chat_downloaded, has_chat_part_file=has_chat_part_file, video_id_to_pct=video_id_to_pct, localtime_hhmmss=localtime_hhmmss, video_id_to_video=video_id_to_video)


@app.route("/downloads/<download_id>", methods=["POST"])
def set_download_status(download_id):
    status = request.form["status"]
    with connection:
        connection.execute("UPDATE downloads SET status = ? WHERE id = ?", (status, download_id))
    return redirect(request.referrer)

@app.route("/downloads")
def downloads():
    cursor = connection.execute("SELECT * FROM sequences")
    sequences = [ Sequence(**seq) for seq in cursor.fetchall() ]

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Downloads{% endblock %}
    {% block body %}
    <main class="mono tall">
    <style>
    </style>
        <h1>Downloads</h1>
        {% include "nav.html" %}
        <div class="box tall">
        {% for sequence in sequences %}
            {#
            {% if sequence['portions'] %}
                {% for portion in sequence['portions'] %}
                <div>{{ portion['title'] }}</div>
                <div class="wide">
                    {% for portionurl in portion['portionurls'] if portionurl['selected'] %}
                    <div>{{ portionurl.user_id }}</div>
                    {% endfor %}
                </div>
                <div class="gray">{{ portion.pretty() }}</div>
                {% endfor %}
            {% endif %}
            #}
            <div class="wide separated">
                <span>{{ sequence['name'] }}</span>
                <a href="{{ url_for('downloads_sequence', sequence_id=sequence['id']) }}">Downloads</a>
                <a href="{{ url_for('view_portions', id=sequence['id']) }}">View {{ sequence['portions'].__len__() }} Portion{{ 's' if sequence['portions'].__len__() != 1 else '' }}</a>
            </div>
        {% endfor %}
        </div>
    </main>
    {% endblock %}""", sequences=sequences)

def portionurl_id_to_docker_command(portionurl_id):
    hostname = socket.gethostname()
    downloads_folder = os.path.join(os.path.dirname(__file__), "static", "downloads")
    return fr"docker cp {hostname}:{downloads_folder}/{portionurl_id}.mp4 C:\Users\vivek\Desktop\claude"

@app.route("/downloads/<sequence_id>")
def downloads_sequence(sequence_id):
    from get_worker_info import get_worker_info
    cursor = connection.execute("SELECT * FROM sequences WHERE id = ?", (sequence_id,))
    sequence = Sequence(**cursor.fetchone())
    worker_table = get_worker_info()
    # docker cp d38142f948ef:/home/vivek/hateoas/hateoas-api.py C:\Users\vivek\Desktop\claude\

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Downloads{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Downloads {{ sequence['name'] }}</h1>

        {% include "nav.html" %}
        <div class="tall">
            <div>{{ sequence['name'] }} has {{ sequence['portions'].__len__() }} portion{{ 's' if sequence['portions'].__len__() != 1 else ''}}</div>
            <div class='tall'>
            {% for worker in worker_table %}
                {% if worker.lock_status == 'stale' %}
                <div>
                    <span class="red">{{ worker.lock_status }}</span>  - {{ worker.lock_filename }} ({{ worker.pid }}) (lock_file exists but PID doesn’t)
                </div>
                {% else %}
                <div>
                    <span class="green">{{ worker.lock_status }}</span>  - {{ worker.lock_filename }} ({{ worker.pid }})
                </div>
                {% endif %}
            {% endfor %}
            {% if worker_table | length == 0 %}
            <div class="error">No workers found</div>
            {% endif %}
            </div>
            {% for portion in sequence['portions'] %}
            <div class="box tall">
                <div>{{ portion.pretty() }}</div>
                <ol class="tall">
                    {% for portionurl in portion.portionurls if portionurl['selected'] %}
                    <li>
                        {% set D = format_portionurl_for_download(portionurl, portion) %}
                        
                        <div>{{ D['user_name'] }} - {{ D['filename'] }} <span class="gray">{{ portionurl.id }}</span></div>
                        {% if downloaded(portionurl.id) %}
                        <div>
                            <span>Download Status:</span>
                            <span class="green">downloaded</span>
                            {% set download_filename = str(portionurl.id) + ".mp4" %}
                            <a href="/static/downloads/{{ download_filename }}">{{ download_filename }}</a>
                        </div>
                        {% if encoded(portionurl.id) %}
                        <div>
                            <span>Encode Status:</span> 
                            <span class="green">encoded</span>
                            {% set encode_filename = portionurl_id_to_filename(portionurl.id) %}
                            <a href="/static/downloads/encodes/{{ encode_filename }}">{{ encode_filename }}</a>
                        </div>
                        {% else %}
                        <div>Encode Status: <span class="red">not encoded</span></div>
                        {% endif %}
                        {% if cropped(portionurl.id) %}
                        <div>
                            <span>Crop Status:</span>
                            <span class="green">cropped</span>
                            {% set crop_filename = portionurl_id_to_filename(portionurl.id) %}
                            <a href="/static/downloads/crops/{{ crop_filename }}">{{ crop_filename }}</a>
                        </div>
                        {% elif in_crop_queue(portionurl.id) %}
                        <div>Crop Status: <span class="yellow">in crop queue</span></div>
                        {% else %}
                        <div>
                            <span>Crop Status: </span>
                            <span class="red">not cropped</span>
                            <a href="{{ url_for('select_rectangle', portionurl_id=portionurl.id) }}">Select Crop Rectangle</a>
                        </div>
                        {% endif %}
                        {#
                        <div>
                            {{ portionurl_id_to_docker_command(portionurl.id) }}
                        </div>
                        #}
                        {% elif partially_downloaded(portionurl.id) %}
                        <div>Status: <span class="yellow">downloading ({{ portionurl.id }})</span></div>
                        {% else %}
                        <div>Status: <span class="red">pending ({{ portionurl.id }})</span></div>
                        {% endif %}
                        <div>
                            <a href="{{ portionurl.url }}?t={{ D['offset'] | hhmmss }}">{{ portionurl.url }}?t={{ D['offset'] | hhmmss }}</a>
                        </div>
                    </li>
                    {% endfor %}
                </ol>
                <div><a href="{{ url_for('view_portion', sequence_id=sequence['id'], portion_id=portion['id']) }}">View Portion</a></div>
            </div>


            {% endfor %}
            <div><a href="{{ url_for('view_portions', id=sequence['id']) }}">View Portions of {{ sequence['name'] }}</a></div>
        </div>
    </main>
    {% endblock %}
    """, sequence=sequence, format_portionurl_for_download=format_portionurl_for_download, str=str, portionurl_downloaded=portionurl_downloaded, worker_table=worker_table, downloaded=downloaded, partially_downloaded=partially_downloaded, portionurl_id_to_docker_command=portionurl_id_to_docker_command, encoded=encoded, cropped=cropped, in_crop_queue=in_crop_queue, portionurl_id_to_filename=portionurl_id_to_filename)


@app.route("/get_synced_videos_html/<video_id>/<offset>")
def get_synced_videos_html(video_id, offset):
    sequence_id = request.args.get("sequence_id")
    offset = int(offset)
    videos = get_synced_videos(video_id, offset)
    cursor = videos_connection.execute("SELECT created_at_epoch FROM videos WHERE id = ?", (video_id,))
    video_created_at_epoch = cursor.fetchone()[0]
    video_created_at_epoch = int(video_created_at_epoch)
    epoch = video_created_at_epoch + offset

    return render_template_string("""
    {% for video in videos %}
    <div>
        <a onclick="load_sync_embed('{{ video.id }}', {{ int(epoch) - int(video.created_at_epoch) }})">
            {{ video.id }} @ {{ (int(epoch) - int(video.created_at_epoch)) | hhmmss}}
        </a> 
        -
        <a href="{{ url_for('sync_video_to_video', video_id=video.id, sequence_id=sequence_id) }}">Sync</a>
        - {{ video.user_name }}
    </div>
    {% endfor %}
    {% if not videos %}
    <div>
        No other videos for video {{ video_id }} @ {{ offset | hhmmss }}
    </div>
    {% endif %}
    """, videos=videos, epoch=epoch, int=int, sequence_id=sequence_id, video_id=video_id, offset=offset)

@app.route("/add_video_to_chat_download_queue/<video_id>", methods=["POST"])
def add_video_to_chat_download_queue(video_id):
    # CREATE TABLE IF NOT EXISTS queue_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, video_id TEXT NOT NULL);
    cursor = connection.cursor()
    cursor.execute("INSERT INTO queue_chat (video_id) VALUES (?)", (video_id,))
    connection.commit()
    return redirect(request.referrer)

@app.route("/chapters/<video_id>")
def chapters(video_id):
    if not usable("data/chapters.json"):
        write({}, "data/chapters.json")
    chapters_dict = read("data/chapters.json")
    if video_id not in chapters_dict:
        return []
    chapters_table = chapters_dict[video_id]
    assert isinstance(chapters_table, list)
    return chapters_table

@app.route("/sync_video_to_video")
def sync_video_to_video(clip_id=None):
    sequence_id = request.args.get("sequence_id")
    video_id = request.args.get("video_id")
    clip_id = request.args.get("clip_id")
    clip = None
    if clip_id:
        cursor = clips_connection.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
        clip = dict(cursor.fetchone())
    cursor = videos_connection.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    video = dict(cursor.fetchone())

    offsets = []
    offsets_downloads_folder = get_offsets_downloads_folder()
    offsets_path = os.path.join(offsets_downloads_folder, f"{video_id}.json")
    if os.path.exists(offsets_path):
        offsets = read(offsets_path)

    graph_payload = {}
    graph_payloads_downloads_folder = get_graph_payloads_downloads_folder()
    graph_payload_path = os.path.join(graph_payloads_downloads_folder, f"{video_id}.json")
    if os.path.exists(graph_payload_path):
        graph_payload = read(graph_payload_path)
        count_dictionaries = [ (D["int_offset"], D["rolling"]) for D in graph_payload['countpairs'] ]
        for D in graph_payload['video_clips']:
            D['x'] = D['start_offset']
            D['y'] = 0.5
            D['z'] = 4 if D['views'] > 100 else 2
        graph_payload['countpairs'] = count_dictionaries


    cursor = connection.execute("SELECT 1 FROM queue_chat WHERE video_id = ?", (video_id,))
    video_id_in_chat_download_queue = cursor.fetchone() is not None

    synced_videos_html = get_synced_videos_html(video_id, 0)

    # graph_payload['chapters'] = chapters(video_id)

    return render_template("sync_video_to_video.html", video=video, offsets=offsets, graph_payload=graph_payload, video_id_in_chat_download_queue=video_id_in_chat_download_queue, synced_videos_html=synced_videos_html, sequence_id=sequence_id, clip=clip)

@app.route("/add_game")
def add_game():
    game_id = request.args.get("game_id")
    if "removed_game_ids" in session and game_id in session["removed_game_ids"]:
        session["removed_game_ids"] = [ game_id for game_id in session["removed_game_ids"] if game_id != game_id ]
    return redirect(request.referrer)

@app.route("/remove_game")
def remove_game():
    game_id = request.args.get("game_id")
    if "removed_game_ids" not in session:
        session["removed_game_ids"] = []
    session["removed_game_ids"] = list(set(session["removed_game_ids"] + [game_id]))
    return redirect(request.referrer)

@app.route("/clips/<clip_id>")
def clip(clip_id):
    cursor = clips_connection.cursor()
    cursor.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
    clip = dict(cursor.fetchone())
    cursor = videos_connection.cursor()
    cursor.execute("SELECT * FROM videos WHERE id = ?", (clip["video_id"],))
    video = dict(cursor.fetchone())
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM sequences")
    sequences = [ Sequence(**seq) for seq in cursor.fetchall() ]

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Clip{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Clip</h1>
        {% include "nav.html" %}
        <div class="box tall">
            <div>Clip of Video by: {{ video['user_name'] }}, created {{ video['created_at_epoch'] | timeago }}, with a duration of: {{ video['duration'] | hhmmss }}</div>
            <div>Offset: {{ (clip['vod_offset'] - clip['duration']) | hhmmss }} ({{ clip['vod_offset'] - clip['duration'] }})</div>
            <div><a href="{{ clip['url'] }}">{{ clip['url'] }}</a></div>
            <div class="wide">
                Sync to:
                <div class="wide separated">
                {% for sequence in sequences %}
                <div><a href="{{ url_for('sync_video_to_video', video_id=clip['video_id'], sequence_id=sequence['id'], clip_id=clip['id']) }}">{{ sequence['name'] }}</a></div>
                {% endfor %}
                </div>
            </div>
            <div>{{ video['title'] }}</div>
            <div>
                <a href="{{ video['thumbnail_url'].replace('%{width}', '640').replace('%{height}', '360') }}">
                <img src="{{ video['thumbnail_url'].replace('%{width}', '640').replace('%{height}', '360') }}" alt="{{ video['title'] }}">
                </a>
            </div>
            <div>{{ clip }}</div>
        </div>
    </main>
    {% endblock %}""", clip=clip, video=video, sequences=sequences)


@app.route("/clips")
def clips():
    cursor = clips_connection.cursor()
    cursor.execute("SELECT * FROM clips")
    if not cursor.fetchone():
        return render_template_string("""
        {% extends "base.html" %}
        {% block title %}Clips{% endblock %}
        {% block body %}
        <main class="mono tall">
            <h1>Clips</h1>
            {% include "nav.html" %}
            <div class="box tall">
                <div class="error">Table `clips` not found in `clips.db`</div>
            </div>
        </main>
        {% endblock %}""")

    cursor = videos_connection.cursor()
    cursor.execute("SELECT user_id, user_name FROM videos GROUP BY user_id ORDER BY user_name")
    users = [dict(row) for row in cursor.fetchall()]

    start_date = request.args.get("start_date", None)
    end_date = request.args.get("end_date", None)
    user_id = request.args.get("user_id", None)
    page = int(request.args.get("page", 1))
    cursor = clips_connection.cursor()
    limit = 10
    offset = (page - 1) * limit

    query = "SELECT * FROM clips"
    count_query = "SELECT COUNT(*) FROM clips"
    conditions = []
    parameters = []
    if start_date:
        conditions.append("created_at_epoch >= ?")
        parameters.append(datetime.strptime(start_date, "%Y-%m-%d").astimezone(ZoneInfo("UTC")).timestamp())
    if end_date:
        conditions.append("created_at_epoch <= ?")
        parameters.append(datetime.strptime(end_date, "%Y-%m-%d").astimezone(ZoneInfo("UTC")).timestamp())
    if user_id:
        conditions.append("broadcaster_id = ?")
        parameters.append(user_id)
    if "removed_game_ids" in session and session["removed_game_ids"]:
        conditions.append("game_id NOT IN ({})".format(",".join(session["removed_game_ids"])))
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        count_query += " WHERE " + " AND ".join(conditions)
    count_parameters = parameters[:]
    query += " ORDER BY view_count DESC"
    query += " LIMIT ? OFFSET ?"
    parameters.extend([limit, offset])
    cursor.execute(query, parameters)

    clips = [dict(clip) for clip in cursor.fetchall()]

    cursor.execute(count_query, count_parameters)
    total = cursor.fetchone()[0]
    page_count = total // limit
    if total % limit:
        page_count += 1
    if page_count == 0:
        page = 0

    pagination = {
        "currentPage": page,
        "currentPageSize": limit,
        "pageCount": page_count,
        "isFirstPage": page == 1,
        "isLastPage": page == page_count,
        "prev": page - 1 if page > 1 else None,
        "next": page + 1 if page < page_count else None,
        "total": total
    }

    links_html = None
    if user_id:
        links_html = users_links_html(user_id)

    cursor = connection.execute("SELECT * FROM sequences")
    sequences = [ Sequence(**seq) for seq in cursor.fetchall() ]

    cursor = games_connection.cursor()
    cursor.execute("SELECT id, name FROM games")
    game_id_to_name = { row['id']: row['name'] for row in cursor.fetchall() }

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Clips{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Clips</h1>
        {% include "nav.html" %}

        {% if links_html %}
        {{ links_html | safe }}
        {% endif %}

        {% if "removed_game_ids" in session and session["removed_game_ids"] %}
        <div class="box tall">
            <div>
                <span>Filtered out games:</span>
                {% for game_id in session["removed_game_ids"] %}
                <span>{{ game_id_to_name[game_id] }}</span>
                {% endfor %}
                </div>
                <div>{{ session["removed_game_ids"] | length }} game{{ "s" if session["removed_game_ids"].__len__() != 1 else "" }} filtered out, go to <a href="{{ url_for('settings') }}">Settings</a> to clear</div>
            </div>

        </div>
        {% endif %}

        <div class="box tall">
            <h3>Pagination</h3>
            <div>
                <div>
                    <div>Start Date: {{ start_date }}</div>
                    <div>End Date: {{ end_date }}</div>
                </div>
                <form action="{{ url_for('clips') }}" method="GET">
                    <input type="date" name="start_date" placeholder="start_date" value="{{ start_date }}">
                    <input type="date" name="end_date" placeholder="end_date" value="{{ end_date }}">
                    {# <input type="text" name="user_id" placeholder="user_id" value="{{ user_id }}"> #}
                    <select name="user_id">
                        <option value="">All</option>
                        {% for user in users %}
                        <option value="{{ user['user_id'] }}" {% if user_id == user['user_id'] %}selected{% endif %}>{{ user['user_name'] }}</option>
                        {% endfor %}
                    </select>
                    <button type="submit">Filter</button>
                </form>
            </div>
            <div>
                {% if pagination['isFirstPage'] or pagination['pageCount'] == 0 %}
                <span class="gray">First</span>
                {% else %}
                <a href="{{ url_for('clips', page=1, start_date=start_date, end_date=end_date, user_id=user_id) }}">First</a>
                {% endif %}
                {% if pagination['prev'] %}
                <a href="{{ url_for('clips', page=pagination['prev'], start_date=start_date, end_date=end_date, user_id=user_id) }}">Prev</a>
                {% else %}
                <span class="gray">Prev</span>
                {% endif %}

                <span>Page {{ pagination['currentPage'] }} of {{ pagination['pageCount'] }}</span>

                {% if pagination['next'] %}
                <a href="{{ url_for('clips', page=pagination['next'], start_date=start_date, end_date=end_date, user_id=user_id) }}">Next</a>
                {% else %}
                <span class="gray">Next</span>
                {% endif %}
                {% if pagination['isLastPage'] %}
                <span class="gray">Last</span>
                {% else %}
                <a href="{{ url_for('clips', page=pagination['pageCount'], start_date=start_date, end_date=end_date, user_id=user_id) }}">Last</a>
                {% endif %}
            </div>
            <div>
                <span>Total: {{ pagination['total'] }}</span>
            </div>
        </div>
        {% for clip in clips %}
        <div class="box tall">
            <div class="font-bold">{{ clip['title'] }}</div>
            <div class="wide separated">
                <div>{{ clip['broadcaster_name'] }}</div>
                <div>{{ clip['view_count'] | abbreviate }} views</div>
                <div>{{ clip['created_at_epoch'] | timeago }}</div>
                <div>{{ clip['duration'] | hhmmss }}</div>
                {% if clip['game_id'] %}
                <div>
                    <span>{{ game_id_to_name[clip['game_id']] }}</span>
                    <a href="{{ url_for('remove_game', game_id=clip['game_id']) }}">Remove</a>
                </div>
                {% endif %}
            </div>
            <div class="tall">
                <div>
                    <a href="{{ clip['url'] }}">Twitch</a>
                    <a href="{{ url_for('clip', clip_id=clip['id']) }}">{{ url_for('clip', clip_id=clip['id']) }}</a>
                </div>
                <div class="wide">
                    Sync to:
                    <div class="wide separated">
                    {% for sequence in sequences %}
                    <div><a href="{{ url_for('sync_video_to_video', video_id=clip['video_id'], sequence_id=sequence['id'], clip_id=clip['id']) }}">{{ sequence['name'] }}</a></div>
                    {% endfor %}
                    </div>
                </div>
            </div>
            <div>
                <a href="{{ clip['thumbnail_url'].replace('%{width}', '640').replace('%{height}', '360') }}">
                    <img height=150 src="{{ clip['thumbnail_url'].replace('%{width}', '640').replace('%{height}', '360') }}" alt="{{ clip['title'] }}">
                </a>
            </div>
            <div>{{ clip }}</div>
        </div>
        {% endfor %}
        {% if not clips %}
        <div class="box">
            No clips found
        </div>
        {% endif %}
    </main>
    {% endblock %}""", clips=clips, pagination=pagination, sequences=sequences, start_date=start_date, end_date=end_date, user_id=user_id, users=users, links_html=links_html, game_id_to_name=game_id_to_name, session=session)










@app.route("/users_video")
def users_video():
    cursor = videos_connection.execute("SELECT user_id, user_name FROM videos GROUP BY user_id ORDER BY user_name")
    users = [dict(row) for row in cursor.fetchall()]
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Users{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Users</h1>
        {% include "nav.html" %}
        <div class="box">
            <div class="grid cols-4">
                {% for user in users %}
                <div class="">
                    <span>{{ user['user_name'] }}</span>
                    <span>{{ user['user_id'] }}</span>
                    <a href="{{ url_for('videos', user_id=user['user_id']) }}">Videos</a>
                    <a href="{{ url_for('clips', user_id=user['user_id']) }}">Clips</a>
                </div>
                {% endfor %}
            </div>
        </div>
    </main>
    {% endblock %}""", users=users)

@app.route("/info")
def info():
    import shutil
    total, used, free = shutil.disk_usage("/")

    # Convert bytes to GB
    one_gb = 1024 * 1024 * 1024
    total_gb = int(total / one_gb)
    used_gb = int(used / one_gb)
    free_gb = int(free / one_gb)
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Info{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Info</h1>
        {% include "nav.html" %}
        <div class="box tall">
            <div>Total: {{ total_gb }} GB</div>
            <div>Used: {{ used_gb }} GB</div>
            <div>Free: {{ free_gb }} GB</div>
        </div>
    </main>
    {% endblock %}""", total_gb=total_gb, used_gb=used_gb, free_gb=free_gb)


@app.route("/static", methods=["GET"])
def staticfiles():
    import os
    here = str(app.static_folder)
    files_recursive = []
    links_recursive = []
    mtimes_recursive = []
    for root, dirs, files in os.walk(here):
        for file in files:
            files_recursive.append(os.path.join(root, file))
            links_recursive.append("static" + os.path.join(root, file).replace(here, ""))
            mtimes_recursive.append(os.path.getmtime(os.path.join(root, file)))
    # sort on `mtime` DESC
    files_recursive, links_recursive, mtimes_recursive = zip(*sorted(zip(files_recursive, links_recursive, mtimes_recursive), key=lambda x: x[2], reverse=True))

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Static Files{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Static Files</h1>
        {% include "nav.html" %}
        <div class="box tall">
            {% for file, link, mtime in zip(files_recursive, links_recursive, mtimes_recursive) %}
            <div class="wide">
                <span>{{ file }}</span>
                <a href="{{ link }}">{{ link }}</a>
                <span class="gray">{{ mtime | timeago }}</span>
            </div>
            {% endfor %}
        </div>
    </main>
    {% endblock %}""", files_recursive=files_recursive, links_recursive=links_recursive, mtimes_recursive=mtimes_recursive, zip=zip)

def readstring(path):
    if not os.path.abspath(path):
        path = rel2abs(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "rb") as f:
        string = f.read().decode("utf-8")
    return string

@app.route("/history")
def history():
    # get available routes
    routes = []
    for rule in app.url_map.iter_rules():
        if not isinstance(rule.methods, set):
            raise ValueError(f"Route {rule} has no methods")
        rule.methods.discard('OPTIONS')
        rule.methods.discard('HEAD')
        routes.append({ 'path': str(rule), 'methods': rule.methods })

    connection = Connection("data/hateoas-history.db")
    # path shouldn’t end with '.css', '.ttf'
    where_query = "WHERE path NOT LIKE '%.css' AND path NOT LIKE '%.ttf' AND path NOT LIKE '%.ico'"
    limit = 30
    results_query = "SELECT MAX(epoch) AS epoch, path FROM history " + where_query + f" GROUP BY path ORDER BY epoch DESC LIMIT {limit};"
    stats_query = "SELECT COUNT(DISTINCT path) FROM history " + where_query + ";"
    cursor = connection.execute(results_query)
    results = [ (row[0], row[1]) for row in cursor.fetchall() ]
    count = connection.execute(stats_query).fetchone()[0]
    connection.close()
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}History{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>History</h1>
        {% include "nav.html" %}
        <style>.list-number { width: 2ch; text-align: right; }</style>
        <div class="box tall">
            <p>Total unique requests: {{ count }}</p>
            {% for epoch, path in results %}
                <div class="tall-0">
                    <div class="wide">
                        <span class="font-bold gray list-number">{{ loop.index }}</span>
                        <a href="{{ path }}">{{ path }}</a>
                        <span class="gray" title="{{ epoch }}">({{ epoch | timeago }})</span>
                    </div>
                </div>
            {% endfor %}
            {% if count > limit %}
                <div class="gray">.. {{ count - limit }} more requests not shown</div>
            {% endif %}
        </div>
    </main>
    {% endblock %}""", results=results, count=count, limit=limit)


@app.route("/add_to_crop_queue", methods=["POST"])
def add_to_crop_queue():
    # CREATE TABLE IF NOT EXISTS queue_crop (id INTEGER PRIMARY KEY AUTOINCREMENT, portionurl_id INTEGER NOT NULL UNIQUE, x INTEGER NOT NULL, y INTEGER NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL, FOREIGN KEY (portionurl_id) REFERENCES portionurls (id) ON DELETE CASCADE) STRICT;
    portionurl_id = request.form.get("portionurl_id")
    x = request.form.get("x")
    y = request.form.get("y")
    width = request.form.get("width")
    height = request.form.get("height")
    cursor = connection.cursor()
    cursor.execute("INSERT INTO queue_crop (portionurl_id, x, y, width, height) VALUES (?, ?, ?, ?, ?)", (portionurl_id, x, y, width, height))
    connection.commit()
    cursor.execute("SELECT portion_id FROM portionurls WHERE id = ?", (portionurl_id,))
    portion_id = cursor.fetchone()[0]
    cursor.execute("SELECT sequence_id FROM portions WHERE id = ?", (portion_id,))
    sequence_id = cursor.fetchone()[0]
    return redirect(url_for("downloads_sequence", sequence_id=sequence_id))
        
@app.route('/select_rectangle/<int:portionurl_id>')
def select_rectangle(portionurl_id):
    video_path = f"/static/downloads/{portionurl_id}.mp4"
    return render_template('select_rectangle.html', video_path=video_path, portionurl_id=portionurl_id)

@app.route('/get_coordinates', methods=['POST'])
def get_coordinates():
    data = request.json
    return {"message": "Coordinates received", "coordinates": data}

@app.route("/settings")
def settings():
    cursor = games_connection.cursor()
    removed_game_ids = session.get("removed_game_ids", [])
    cursor.execute("SELECT id, name FROM games WHERE id IN ({})".format(",".join(removed_game_ids)))
    removed_games = [dict(row) for row in cursor.fetchall()]
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Settings{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Settings</h1>
        {% include "nav.html" %}
        <div class="box tall">
            <h2>Removed Games (for /clips view)</h2>
            {% for game in removed_games %}
            <div>
                <span>{{ game['name'] }}</span>
                <a href="{{ url_for('add_game', game_id=game['id']) }}">Add</a>
            </div>
            {% endfor %}
            {% if not removed_games %}
            <div>No games removed</div>
            {% endif %}
        </div>
        <div class="box">
            {{ session }}
        </div>
    </main>
    {% endblock %}""", session=session, removed_games=removed_games)

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
    sql_filename = rel2abs("main.sql")
    sql_script = readstring(sql_filename)
    connection.executescript(sql_script)
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=True)

if __name__ == "__main__":
    main()
