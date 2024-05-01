
from dbutils import Connection

connection = Connection("data/tasks_test.db")

# CREATE TABLE tasks ( id INTEGER PRIMARY KEY AUTOINCREMENT);
connection.execute("DELETE FROM tasks;")
count = 100_000
connection.executemany("INSERT INTO tasks DEFAULT VALUES", [() for _ in range(count)])
connection.commit()

cursor = connection.execute("SELECT COUNT(*) FROM tasks")
count = cursor.fetchone()[0]
print(f"Total rows in tasks: {count:,}")
# first row, last row

cursor = connection.execute("SELECT * FROM tasks LIMIT 1")
print("First row:", dict(cursor.fetchone()))

cursor = connection.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT 1")
print("Last row:", dict(cursor.fetchone()))
