
from datetime import datetime
import time
from flask import request
from flask import render_template_string
from flask import render_template
from flask import Flask
from flask import redirect
from flask import url_for
from flask_cors import CORS
from dbutils import Connection
from Types import Sequence, Portion, PortionUrl
from portionurl_to_download_path import downloaded, partially_downloaded
from worker_utils import get_graph_payloads_downloads_folder, get_offsets_downloads_folder, has_chat_part_file, is_chat_downloaded
from typing import TypedDict
from waivek import read, rel2abs
import os.path


app = Flask(__name__)
app.config['Access-Control-Allow-Origin'] = '*'
CORS(app)

connection = Connection('data/main.db')
videos_connection = Connection('data/videos.db')
clips_connection = Connection('data/clips.db')


def get_download_filename(portionurl: PortionUrl, portion: Portion, video: dict) -> str:
    from slugify import slugify
    order = portion.order
    order_padded = str(order).zfill(2)
    user_name = video["user_name"]
    title = portion.title
    title_slug = slugify(title, separator="_")
    video_id = video["id"]
    offset = portion.epoch - video["created_at_epoch"]
    offset_hhmmss = hhmmss(offset)
    return ".".join([order_padded, title_slug, user_name, video_id, offset_hhmmss, "mp4"])


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

@app.route("/downloads/<download_id>", methods=["POST"])
def set_download_status(download_id):
    status = request.form["status"]
    with connection:
        connection.execute("UPDATE downloads SET status = ? WHERE id = ?", (status, download_id))
    return redirect(request.referrer)

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
            <div><a href="{{ url_for('view_portion', sequence_id=sequence['id'], portion_id=portion['id']) }}">View Portion with {{ extra['portionurls'] | length }} URL{{ 's' if extra['portionurls'] | length != 1 else '' }}</a></div>
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
            <div>Video by: {{ video['user_name'] }}, created {{ video['created_at_epoch'] | timeago }}, with a duration of: {{ video['duration'] | hhmmss }}</div>
            <div>{{ video['title'] }}</div>
            <div>
                <img src="{{ thumbnail_url }}" alt="{{ video['title'] }}">
            </div>
            <div>{{ video }}</div>
        </div>
        <div class="box tall">
            <!-- dynamic form for create_portion where sequence_id is selected via dropdown -->
            {% for sequence in sequences %}
            <div><a href="{{ url_for('form_create_portion', sequence_id=sequence['id'], video_id=video['id']) }}">Add to {{ sequence['name'] }}</a></div>
            {% endfor %}
            {% if not sequences %}
            <div>No sequences found, so we cannot create a portion</div>
            <div><a href="{{ url_for('view_sequences') }}">Create a sequence</a></div>
            {% endif %}
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

    cursor = connection.execute("SELECT * FROM sequences")
    sequences = [ Sequence(**seq) for seq in cursor.fetchall() ]

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
            <div class="tall">
                <div><a href="{{ url_for('video', id=video['id']) }}">View</a></div>
                <div class="wide">

                    <div>Sync to:</div>
                    {% for sequence in sequences %}
                    <div><a href="{{ url_for('sync_video_to_video', video_id=video['id'], sequence_id=sequence['id']) }}">{{ sequence['name'] }}</a></div>
                    {% endfor %}

                    {# <a href="{{ url_for('sync_video_to_video', video_id=video['id']) }}">Sync</a> #}
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
    {% endblock %}""", videos=videos, pagination=pagination, sequences=sequences)

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
            {% for row in queue_chat %}
            <ol>
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
            </ol>
            {% endfor %}
        </div>
    </main>
    {% endblock %}""", queue_chat=queue_chat, worker_table=worker_table, is_chat_downloaded=is_chat_downloaded, has_chat_part_file=has_chat_part_file, video_id_to_pct=video_id_to_pct, localtime_hhmmss=localtime_hhmmss, video_id_to_video=video_id_to_video)


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
        {% for sequence in sequences %}
        <div class="box tall">
            <div>{{ sequence['name'] }} has {{ sequence['portions'].__len__() }} portion{{ 's' if sequence['portions'].__len__() != 1 else ''}}</div>
            {% if sequence['portions'] %}
            <ol>
                {% for portion in sequence['portions'] %}
                <li>
                    <div>{{ portion['title'] }}</div>
                    <div class="wide">
                        {% for portionurl in portion['portionurls'] if portionurl['selected'] %}
                        <div>{{ portionurl.user_id }}</div>
                        {% endfor %}
                    </div>
                    <div class="gray">{{ portion.pretty() }}</div>
                </li>
                {% endfor %}:
            </ol>
            {% endif %}
            <div><a href="{{ url_for('downloads_sequence', sequence_id=sequence['id']) }}">Download {{ sequence['name'] }}</a></div>
            <div><a href="{{ url_for('view_portions', id=sequence['id']) }}">View Portions of {{ sequence['name'] }}</a></div>
        </div>
        {% endfor %}
    </main>
    {% endblock %}""", sequences=sequences)

@app.route("/downloads/<sequence_id>")
def downloads_sequence(sequence_id):
    from get_worker_info import get_worker_info
    cursor = connection.execute("SELECT * FROM sequences WHERE id = ?", (sequence_id,))
    sequence = Sequence(**cursor.fetchone())
    worker_table = get_worker_info()

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Downloads{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Downloads {{ sequence['name'] }}</h1>
        <style>
        .pending { color: yellow; }
        .complete { color: lightgreen; }
        </style>

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
            <div class="box">
                <div>{{ portion.pretty() }}</div>
                <ol class="tall">
                    {% for portionurl in portion.portionurls if portionurl['selected'] %}
                    <li>
                        {% set D = format_portionurl_for_download(portionurl, portion) %}
                        
                        <div>{{ D['user_name'] }} - {{ D['filename'] }} <span class="gray">{{ portionurl.id }}</span></div>
                        {% if downloaded(portionurl.id) %}
                        <div>Status: <span class="green">complete ({{ portionurl.id }})</span></div>
                        {% elif partially_downloaded(portionurl.id) %}
                        <div>Status: <span class="yellow">downloading ({{ portionurl.id }})</span></div>
                        {% else %}
                        <div>Status: <span class="red">pending ({{ portionurl.id }})</span></div>
                        {% endif %}

                        <div>
                            {% if portionurl_downloaded(portionurl) %}
                            <a href="{{ url_for('static', filename='downloads/' + str(portionurl.id) + '.mp4') }}">
                                {{ url_for('static', filename='downloads/' + str(portionurl.id) + '.mp4') }}
                            </a>
                            {% else %}
                            <span class="gray">{{ url_for('static', filename='downloads/' + str(portionurl.id) + '.mp4') }}</span>
                            {% endif %}
                        </div>

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
    {% endblock %}""", sequence=sequence, format_portionurl_for_download=format_portionurl_for_download, str=str, portionurl_downloaded=portionurl_downloaded, worker_table=worker_table, downloaded=downloaded, partially_downloaded=partially_downloaded)


@app.route("/get_synced_videos_html/<video_id>/<offset>")
def get_synced_videos_html(video_id, offset):
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
        <a href="{{ url_for('sync_video_to_video', video_id=video.id) }}">Sync</a>
        - {{ video.user_name }}
    </div>
    {% endfor %}""", videos=videos, epoch=epoch, int=int)

@app.route("/add_video_to_chat_download_queue/<video_id>", methods=["POST"])
def add_video_to_chat_download_queue(video_id):
    # CREATE TABLE IF NOT EXISTS queue_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, video_id TEXT NOT NULL);
    cursor = connection.cursor()
    cursor.execute("INSERT INTO queue_chat (video_id) VALUES (?)", (video_id,))
    connection.commit()
    return redirect(request.referrer)

@app.route("/sync_video_to_video")
def sync_video_to_video():
    sequence_id = request.args.get("sequence_id")
    video_id = request.args.get("video_id")
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

    return render_template("sync_video_to_video.html", video=video, offsets=offsets, graph_payload=graph_payload, video_id_in_chat_download_queue=video_id_in_chat_download_queue, synced_videos_html=synced_videos_html, sequence_id=sequence_id)

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
    start_date = request.args.get("start_date", None)
    end_date = request.args.get("end_date", None)
    user_id = request.args.get("user_id", None)
    page = int(request.args.get("page", 1))
    cursor = clips_connection.cursor()
    limit = 10
    offset = (page - 1) * limit

    query = "SELECT * FROM clips"
    conditions = []
    parameters = []
    if start_date:
        conditions.append("created_at_epoch >= ?")
        parameters.append(start_date)
    if end_date:
        conditions.append("created_at_epoch <= ?")
        parameters.append(end_date)
    if user_id:
        conditions.append("broadcaster_id = ?")
        parameters.append(user_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY view_count DESC"
    query += " LIMIT ? OFFSET ?"
    parameters.extend([limit, offset])
    cursor.execute(query, parameters)

    clips = [dict(clip) for clip in cursor.fetchall()]


    cursor.execute("SELECT COUNT(*) FROM clips")
    total = cursor.fetchone()[0]
    page_count = total // limit
    if total % limit:
        page_count += 1

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

    cursor = connection.execute("SELECT * FROM sequences")
    sequences = [ Sequence(**seq) for seq in cursor.fetchall() ]

    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Clips{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Clips</h1>
        {% include "nav.html" %}
        <div class="box tall">
            <h3>Pagination</h3>
            <div>
                <form action="{{ url_for('clips') }}" method="GET">
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
        {% for clip in clips %}
        <div class="box tall">
            <div class="tall">
                {# <div><a href="{{ url_for('clip', id=clip['id']) }}">View</a></div> #}
                <div class="wide">
                    <div>Sync to:</div>
                    {% for sequence in sequences %}
                    {# <div><a href="{{ url_for('sync_clip_to_video', clip_id=clip['id'], sequence_id=sequence['id']) }}">{{ sequence['name'] }}</a></div> #}
                    {% endfor %}
                </div>
            </div>
            <div>Clip of: {{ clip['broadcaster_name'] }}, created {{ clip['created_at_epoch'] | timeago }}, with a duration of: {{ clip['duration'] | hhmmss }}</div>
            <div>{{ clip['title'] }}</div>
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
    {% endblock %}""", clips=clips, pagination=pagination, sequences=sequences)












@app.route("/users_video")
def users_video():
    cursor = videos_connection.execute("SELECT user_id, user_name FROM videos GROUP BY user_id")
    users = [dict(row) for row in cursor.fetchall()]
    return render_template_string("""
    {% extends "base.html" %}
    {% block title %}Users{% endblock %}
    {% block body %}
    <main class="mono tall">
        <h1>Users</h1>
        {% include "nav.html" %}
        <div class="box tall">
            {% for user in users %}
            <div class="wide">
                <span>{{ user['user_name'] }}</span>
                <span>{{ user['user_id'] }}</span>
                <a href="{{ url_for('videos', user_id=user['user_id']) }}">Videos</a>
                <a href="{{ url_for('clips', user_id=user['user_id']) }}">Clips</a>
            </div>
            {% endfor %}
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

def main():
    sql_filename = rel2abs("main.sql")
    sql_script = readstring(sql_filename)
    connection.executescript(sql_script)
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=True)

if __name__ == "__main__":
    main()
