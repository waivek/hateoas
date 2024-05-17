
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
from download_portionurl import download_portionurl_interruptable

def log(message, *args):
    log_string = f"[download_worker.py] [loop_forever_unless_file_changes] [PID={os.getpid()}] {message}"
    print(log_string, *args)

def get_self_hash() -> str:
    with open(__file__, "r") as f:
        contents = f.read()

    file_hash = hashlib.md5(contents.encode()).hexdigest()
    return file_hash

def get_portionurl_id_from_queue():
    # CREATE TABLE download_queue (
    #     id INTEGER PRIMARY KEY AUTOINCREMENT,
    #     portionurl_id INTEGER NOT NULL
    # ) STRICT;

    connection.execute("BEGIN IMMEDIATE TRANSACTION;")
    cursor = connection.execute("SELECT portionurl_id FROM download_queue LIMIT 1;")
    row = cursor.fetchone()
    if row is None:
        connection.execute("END TRANSACTION;")
        return None
    portionurl_id = row[0]
    connection.execute("DELETE FROM download_queue WHERE portionurl_id = ?;", (portionurl_id,))
    connection.execute("END TRANSACTION;")
    connection.commit()
    return portionurl_id

def loop():


    def cleanup(signum: int, frame: FrameType | None):
        nonlocal allow_loop
        global connection
        allow_loop = False
        connection.close()
        sys.exit(0)

    allow_loop = True
    original_file_hash = get_self_hash()

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    while True:

        if original_file_hash != get_self_hash():
            log("File has changed.")
            cleanup(0, None)

        if not allow_loop:
            log("Received signal to stop.")
            break

        portionurl_id = get_portionurl_id_from_queue()
        if portionurl_id:
            log("Downloading portionurl_id: %s", portionurl_id)
            download_portionurl_interruptable(portionurl_id)
        time.sleep(1)
        
    log("File changed, exiting.")
    sys.exit(0)

def main():
    loop()

connection = Connection("data/main.db")

if __name__ == "__main__":
    main()
