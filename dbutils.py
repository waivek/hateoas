
import os
import sqlite3 as sq3
import pysqlite3 as sqlite3
import typing

def Connection(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False) # type: ignore
    connection.row_factory = sqlite3.Row                        # type: ignore
    return typing.cast(sq3.Connection, connection)

def key_id():
    import string
    import random
    key_length = 8
    key = ''.join(random.choices(string.ascii_letters + string.digits, k=key_length))
