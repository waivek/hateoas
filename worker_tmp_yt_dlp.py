import subprocess
import time
import os

from waivek import Connection
from worker_utils import log
from tmp_utils import queue_get_one, queue_done

connection = Connection("data/tmp_yt_dlp.db")
with connection:
    connection.execute("DROP TABLE IF EXISTS queue_yt_dlp")
    connection.execute("CREATE TABLE IF NOT EXISTS queue_yt_dlp (video_id TEXT PRIMARY KEY, pid INTEGER)")

log("Watching table queue_yt_dlp in data/tmp_yt_dlp.db")
while True:
    video_id = queue_get_one(connection, "queue_yt_dlp", "video_id", os.getpid())
    if not video_id:
        time.sleep(1)
        continue
    result = subprocess.run(["youtube-dl", "-f", "bestaudio", "-o", f"tmp/{video_id}.%(ext)s", f"https://www.youtube.com/watch?v={video_id}"])
    log(f"{result.returncode} {video_id}")
    if result.returncode == 0:
        queue_done(connection, "queue_yt_dlp", "video_id", video_id)
