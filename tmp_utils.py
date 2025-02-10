
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlite3 import Connection

# connection.execute("CREATE TABLE IF NOT EXISTS queue_yt_dlp (video_id TEXT PRIMARY KEY, pid INTEGER)")
def queue_get_one(connection: "Connection", table_name: str, primary_key: str, pid: int):
    with connection:
        cursor = connection.execute(f"SELECT {primary_key} FROM {table_name} LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return None
        connection.execute(f"UPDATE {table_name} SET pid = ? WHERE {primary_key} = ?", (pid, row[0]))
        return row[0]

def queue_done(connection: "Connection", table_name: str, primary_key: str, identifier):
    with connection:
        # connection.execute(f"DELETE FROM {table_name} WHERE {primary_key} = ?", (identifier,))
        pass
