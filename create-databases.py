
import os
import os.path
from dbutils import Connection
import sqlite3
from waivek import Code

def get_list_of_sql_files_in_cwd():
    return [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.sql')]

def db_table_count(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
    return cursor.fetchone()[0]

def db_table_names(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cursor.fetchall()]

os.makedirs('data', exist_ok=True)

paths = get_list_of_sql_files_in_cwd()
db_paths = []
for path in paths:
    db_paths.append(f"data/{path[:-4]}.db")

for db_path, sql_path in zip(db_paths, paths):

    print(f"{sql_path} -> {db_path}")
    connection = Connection(db_path)
    table_names = db_table_names(connection)
    table_count = len(table_names)
    if table_count > 0:
        print(f"... Database {db_path} already has {table_count} tables, skipping...")
        print(f"... Tables: {table_names}")
        print()
        continue

    with open(sql_path, 'r') as f:
        sql = f.read()
    with connection:
        connection.executescript(sql)
    print(Code.LIGHTGREEN_EX + f"... Database {db_path} created with tables: {db_table_names(connection)}")
    print()


