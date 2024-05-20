
from dbutils import Connection
from portionurl_to_download_path import downloaded, downloads_folder
import os.path
import time
import sys
import signal
import os
connection = Connection("data/main.db")

def partially_downloaded(portionurl_id):
    mp4_partial_path = os.path.join(downloads_folder(), f"{portionurl_id}.mp4.part")
    webm_partial_path = os.path.join(downloads_folder(), f"{portionurl_id}.webm.part")
    return os.path.exists(mp4_partial_path) or os.path.exists(webm_partial_path)


def refresh_downloads_table():
    cursor = connection.execute("SELECT portionurl_id FROM downloads;")
    portionurl_ids = [row[0] for row in cursor.fetchall()]
    for portionurl_id in portionurl_ids:
        if downloaded(portionurl_id) and partially_downloaded(portionurl_id):
            raise Exception(f"Both path and part file exist for portionurl_id {portionurl_id}.")
        elif not downloaded(portionurl_id) and not partially_downloaded(portionurl_id):
            cursor = connection.execute("SELECT status FROM downloads WHERE portionurl_id = ?;", (portionurl_id,))
            status = cursor.fetchone()[0]
            if status in [ "downloading", "complete" ]:
                connection.execute("UPDATE downloads SET status = 'pending' WHERE portionurl_id = ?;", (portionurl_id,))
        elif downloaded(portionurl_id) and not partially_downloaded(portionurl_id):
            connection.execute("UPDATE downloads SET status = 'complete' WHERE portionurl_id = ?;", (portionurl_id,))
        elif not downloaded(portionurl_id) and partially_downloaded(portionurl_id):
            connection.execute("UPDATE downloads SET status = 'downloading' WHERE portionurl_id = ?;", (portionurl_id,))
        else:
            assert False, "Should not reach here."
    connection.commit()

def self_hash():
    import hashlib
    with open(__file__, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

class LockFile:

    def __init__(self):
        self.lock_file_path = "/tmp/refresh_downloads_table.lock"
        if self.exists():
            self.remove_lock_file_if_pid_does_not_exist()
        assert not self.exists(), f"Lock file {self.lock_file_path} already exists."

    def remove_lock_file_if_pid_does_not_exist(self):
        from waivek import Code
        D = self.parse_lock_file()
        PID = int(D["PID"])
        if not os.path.exists(f"/proc/{PID}"):
            print(Code.RED + f"Removing lock file {self.lock_file_path} because PID {PID} does not exist.")
            self.release()

    def exists(self):
        return os.path.exists(self.lock_file_path)

    def acquire(self):
        PID = os.getpid()
        time_string = time.ctime()
        time_epoch = int(time.time())
        lines = [ f"PID: {PID}", f"Time: {time_string}", f"Epoch: {time_epoch}" ]
        with open(self.lock_file_path, "w") as f:
            f.write("\n".join(lines))

    def release(self):
        os.remove(self.lock_file_path)

    def parse_lock_file(self):
        with open(self.lock_file_path) as f:
            lines = f.readlines()
        D = {}
        for line in lines:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            D[key] = value
        return D

def loop():

    lock_file = LockFile()

    def cleanup(signum, frame):
        log(f"Received signal {signum}.")
        lock_file.release()

    lock_file.acquire()

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    original_hash = self_hash()

    while True:
        if not lock_file.exists():
            log("Lock file has been deleted.")
            break
        if original_hash != self_hash():
            log("File has changed.")
            cleanup(None, None)
            break
        refresh_downloads_table()
        log("Refreshed downloads table.")
        time.sleep(1)

def log(message, *args):
    print(f"{int(time.time())} refresh_downloads_table.py {message}", *args)

if __name__ == "__main__":
    log(f"{sys.argv = }")
    if len(sys.argv) == 1:
        refresh_downloads_table()
        log("Refreshed downloads table.")
    elif sys.argv[1] == "loop":
        loop()

