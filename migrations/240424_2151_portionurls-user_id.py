import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from dbutils import Connection


connection = Connection("data/main.db")
videos_connection = Connection("data/videos.db")

# add NOT NULL constraint to `user_id` column in `portionurls` table

cursor = connection.execute("SELECT id,url FROM portionurls")
video_ids = []
for id,url in cursor.fetchall():
    video_id = url.replace("https://www.youtube.com/watch?v=", "").replace("https://www.twitch.tv/videos/", "")
    video_ids.append(video_id)
    row = videos_connection.execute("SELECT user_id FROM videos WHERE id = ?", (video_id,)).fetchone()
    user_id = row[0]
    connection.execute("UPDATE portionurls SET user_id = ? WHERE id = ?", (user_id, id))

connection.commit()
