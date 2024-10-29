import time
import psutil
from waivek import Connection

worker_connection = Connection("data/worker.db")

def worker_init():
    global worker_connection
    with worker_connection:
        worker_connection.execute("CREATE TABLE IF NOT EXISTS workers (filename TEXT UNIQUE, pid INTEGER UNIQUE, started_at INTEGER) STRICT;")

def worker_purge():
    global worker_connection
    with worker_connection:
        cursor = worker_connection.execute("SELECT pid FROM workers;")
        stale_pids = [ pid for pid, in cursor.fetchall() if not psutil.pid_exists(pid) ]
        if stale_pids:
            print("Removed %d stale workers with pids: %s" % (len(stale_pids), ", ".join(map(str, stale_pids))))
        worker_connection.executemany("DELETE FROM workers WHERE pid = ?;", [(pid,) for pid in stale_pids])

def worker_start(filename, pid):
    global worker_connection
    worker_purge()
    with worker_connection:
        worker_connection.execute("INSERT INTO workers (filename, pid, started_at) VALUES (?, ?, ?);", (filename, pid, int(time.time())))

def worker_exists(filename):
    global worker_connection
    worker_purge()
    with worker_connection:
        cursor = worker_connection.execute("SELECT pid FROM workers WHERE filename = ?;", (filename,))
        return cursor.fetchone() is not None
