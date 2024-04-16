
import os
import pysqlite3 as sqlite3

def Connection(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False) # type: ignore
    connection.row_factory = sqlite3.Row # type: ignore
    return connection

