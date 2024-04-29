
# reloads if file changes, this is done by simply exiting when the file changes and `crontab` keeps starting it
# listens for interuption signals and cleans up

from dbutils import Connection
import signal
import os
import hashlib
from waivek import ic
from waivek import ib, rel2abs
import sys
from types import FrameType
import time
from download_portionurl import download_portionurl

download_workers_connection = Connection("data/download_workers.db")
connection = Connection("data/main.db")

def to_log_string(message):
    global worker_id
    return f"[download_worker.py] [loop_forever_unless_file_changes] [worker_id={worker_id}] {message}"

def log(message, *args):
    print(to_log_string(message), *args)

def acquire_worker_id_or_raise(max_workers=4):
    global worker_id
    with download_workers_connection:
        cursor = download_workers_connection.execute("SELECT COUNT(*) FROM online_workers;")
        count = cursor.fetchone()[0]
        if count >= max_workers:
            # this will be hit once a minute since crontb keeps starting the script, this allows us to reload the file when it changes
            raise Exception(f"[download_worker.py] [acquire_worker_id_or_raise] Max workers reached: {max_workers}")
        cursor = download_workers_connection.execute("INSERT INTO online_workers DEFAULT VALUES;")
        assert cursor.lastrowid
        worker_id = cursor.lastrowid

def cleanup(signum: int, frame: FrameType | None):
    global worker_id
    with download_workers_connection:
        download_workers_connection.execute("DELETE FROM online_workers WHERE id = ?;", (worker_id,))
    log(f"Worker {worker_id} cleaned up.")
    sys.exit(0)

def get_self_hash() -> str:
    with open(__file__, "r") as f:
        contents = f.read()

    file_hash = hashlib.md5(contents.encode()).hexdigest()
    return file_hash

def get_portionurl_id():
    # db: download_workers, tables: online_workers(id), acquired_portionurl_ids(worker_id, portionurl_id)
    # db: main, tables: downloads (id, portionurl_id, status)
    # check table `downloads` for a portionurl_id that is not downloaded and is not being downloaded by another worker

    row = None
    with download_workers_connection, connection:
        cursor = download_workers_connection.execute("SELECT portionurl_id FROM acquired_portionurl_ids;")
        acquired_portionurl_ids = [ row[0] for row in cursor.fetchall() ]
        if len(acquired_portionurl_ids) == 0:
            cursor = connection.execute("SELECT portionurl_id FROM downloads WHERE status = 'pending' LIMIT 1;")
            row = cursor.fetchone()
        else:
            cursor = connection.execute("SELECT portionurl_id FROM downloads WHERE status = 'pending' AND portionurl_id NOT IN (?);", (acquired_portionurl_ids,))
            row = cursor.fetchone()
    if row is None:
        return None
    portionurl_id = row[0]
    return portionurl_id

def loop_forever_unless_file_changes(original_file_hash: str):
    global worker_id
    while get_self_hash() == original_file_hash:
        portionurl_id = get_portionurl_id()
        if portionurl_id:
            # acquire the portionurl_id
            with download_workers_connection:
                download_workers_connection.execute("INSERT INTO acquired_portionurl_ids VALUES (?, ?);", (worker_id, portionurl_id))
            download_portionurl(portionurl_id)
            with download_workers_connection:
                download_workers_connection.execute("DELETE FROM acquired_portionurl_ids WHERE portionurl_id = ?;", (portionurl_id,))
        time.sleep(1)
        
    log("File changed, exiting.")
    sys.exit(0)

worker_id = acquire_worker_id_or_raise(max_workers=4)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

loop_forever_unless_file_changes(get_self_hash())


