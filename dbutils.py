
import os
import os.path
import sqlite3 as sq3
import pysqlite3 as sqlite3
import typing
import sys

def ensure_db_dir_exists(path):
    db_dir = os.path.dirname(path)
    if not os.path.exists(db_dir):
        raise Exception(f"Directory {db_dir} does not exist")

def get_connection(path):
    connection = sqlite3.connect(path, check_same_thread=False) # type: ignore
    connection.row_factory = sqlite3.Row                        # type: ignore
    connection.execute("PRAGMA foreign_keys = ON") # pragma foreign_keys=ON is needed for each connection
    return typing.cast(sq3.Connection, connection)

def to_absolute_path(path, caller_frame):
    if os.path.isabs(path):
        return path
    caller_path = str(caller_frame.f_globals.get('__file__'))
    caller_dir = os.path.dirname(caller_path)
    return os.path.join(caller_dir, path)

def Connection(path):
    if ":memory:" in path:
        return get_connection(path)

    caller_frame = sys._getframe(1)
    path = to_absolute_path(path, caller_frame)

    ensure_db_dir_exists(path)

    return get_connection(path)

def key_id():
    import string
    import random
    key_length = 8
    key = ''.join(random.choices(string.ascii_letters + string.digits, k=key_length))

