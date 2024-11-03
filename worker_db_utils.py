import time
import psutil
from waivek import Connection

worker_connection = Connection("data/workers.db")
jobs_connection = Connection("data/jobs.db")

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

def jobs_db_init():
    global jobs_connection
    with jobs_connection:
        jobs_connection.execute("CREATE TABLE IF NOT EXISTS jobs (job_id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL, pid INTEGER, exit_code INTEGER, task_id TEXT NOT NULL, started_at INTEGER NOT NULL, ended_at INTEGER) STRICT;")

def job_start(filename, pid, task_id) -> int:
    global jobs_connection
    with jobs_connection:
        cursor = jobs_connection.execute("INSERT INTO jobs (filename, pid, exit_code, task_id, started_at) VALUES (?, ?, NULL, ?, ?);", (filename, pid, task_id, int(time.time())))
        assert cursor.lastrowid, f"[job_start] [filename={filename}] [pid={pid}] [task_id={task_id}] failed as lastrowid is None"
        return cursor.lastrowid

def job_end(job_id, exit_code):
    global jobs_connection
    with jobs_connection:
        jobs_connection.execute("UPDATE jobs SET exit_code = ?, ended_at = ? WHERE job_id = ?;", (exit_code, int(time.time()), job_id))
