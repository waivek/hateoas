
from dbutils import Connection
import time
import signal

connection = Connection("data/tasks_test.db")

# CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT NOT NULL DEFAULT 'incomplete' CHECK (status IN ('incomplete', 'progress', 'complete')));

# CREATE TABLE completed_tasks (id INTEGER UNIQUE);

def array_concatenation_error():
    L = [ "a",
         "b", 
         "c" 
         ]
    return L

def cleanup():
    # check if connection is open
    global allow_loop
    allow_loop = False

signal.signal(signal.SIGINT, lambda signum, frame: cleanup())
signal.signal(signal.SIGTERM, lambda signum, frame: cleanup())

task_time_ms = 10

allow_loop = True

while allow_loop:

    task_id = None
    connection.execute("BEGIN IMMEDIATE TRANSACTION;")
    cursor = connection.execute("SELECT id FROM tasks WHERE status='incomplete' LIMIT 1;")
    if cursor is None:
        connection.execute("END TRANSACTION;")
        break
    task_id = cursor.fetchone()[0]
    connection.execute("UPDATE tasks SET status='progress' WHERE id=?;", (task_id,))
    connection.execute("END TRANSACTION;")
    connection.commit()

    assert task_id is not None, "Task ID is None."
    time.sleep(task_time_ms / 1000)
    connection.execute("UPDATE tasks SET status='complete' WHERE id=?;", (task_id,))
    connection.execute("INSERT INTO completed_tasks (id) VALUES (?);", (task_id,))
    connection.commit()
    print(f"Task {task_id} completed.")

