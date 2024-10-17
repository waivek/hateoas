from waivek import Timer

from query_user_ids import query_user_ids   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
from auth import get_helix_client_id_and_oath_token
from waivek import aget
from waivek import db_init
from waivek import insert_dictionaries
from waivek import readlines
from filter_out_existing_records import filter_out_existing_records
import requests

class Paths:
    def __init__(self):
        self.db_path = rel2abs('data/clips.db')
        self.schema_path = rel2abs('schema/clips.sql')

paths = Paths()

def to_rfc_3339(dt):
    dt = dt.replace(microsecond=0)
    s = dt.isoformat()+"Z"
    return s

def create_table_if_not_exists(cursor):
    table_name = "clips"
    table_exists = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'".format(table_name=table_name)).fetchone()
    if not table_exists:
        schema_sql_lines = readlines(paths.schema_path)
        schema_sql = "\n".join(schema_sql_lines)
        cursor.executescript(schema_sql)
        print(f"Creating table '{table_name}'")
        print(f"Executing schema '{paths.schema_path}'")

def get_clips_url(username, started_at, ended_at):
    user_ids = query_user_ids([username])
    user_id = user_ids[0]
    started_at = to_rfc_3339(started_at)
    ended_at = to_rfc_3339(ended_at)
    url = f"https://api.twitch.tv/helix/clips?broadcaster_id={user_id}&first=100&started_at={started_at}&ended_at={ended_at}"
    return url

def get_clips(usernames):
    from datetime import timedelta
    from datetime import datetime
    client_id, oath_token = get_helix_client_id_and_oath_token()
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    urls = [ get_clips_url(username, start_date, end_date) for username in usernames ]
    headers = { "Client-ID" : client_id, "Authorization" : "Bearer " + oath_token }
    responses = aget(urls, cache=False, url2header=lambda url:headers)
    connection = db_init(paths.db_path)
    cursor = connection.cursor()
    # cursor.execute("DROP TABLE IF EXISTS clips;")
    create_table_if_not_exists(cursor)
    # CREATE TABLE "clips" (id TEXT NOT NULL PRIMARY KEY, url TEXT NOT NULL, embed_url TEXT NOT NULL, broadcaster_id TEXT NOT NULL, broadcaster_name TEXT NOT NULL, creator_id TEXT NOT NULL, creator_name TEXT NOT NULL, game_id TEXT NOT NULL, -- the game_id can be '' language TEXT NOT NULL, title TEXT NOT NULL, view_count INTEGER NOT NULL, created_at TEXT NOT NULL, thumbnail_url TEXT NOT NULL, language TEXT NOT NULL, duration INTEGER NOT NULL, created_at_epoch INTEGER NOT NULL, video_id TEXT, vod_offset INTEGER) STRICT;
    for resp in responses:
        table = resp['data']
        for row in table:
            created_at_utc_string = row["created_at"] # Format: 2023-07-28T16:38:57Z
            created_at_utc = datetime.strptime(created_at_utc_string, "%Y-%m-%dT%H:%M:%SZ")
            created_at_epoch = int(created_at_utc.timestamp())
            row["duration"] = int(row["duration"])
            row["created_at_epoch"] = created_at_epoch
            if row["game_id"] == "":
                row["game_id"] = None

        table = filter_out_existing_records(cursor, table, 'clips')

        cursor.executemany("INSERT INTO clips (id, url, embed_url, broadcaster_id, broadcaster_name, creator_id, creator_name, game_id, language, title, view_count, created_at, thumbnail_url, duration, created_at_epoch, video_id, vod_offset) VALUES (:id, :url, :embed_url, :broadcaster_id, :broadcaster_name, :creator_id, :creator_name, :game_id, :language, :title, :view_count, :created_at, :thumbnail_url, :duration, :created_at_epoch, :video_id, :vod_offset)", table)

    connection.commit()
    query = "SELECT * FROM clips LIMIT 5"
    cursor.execute(query)
    rows = cursor.fetchall()
    table = [ dict(row) for row in rows ]
    ic(table)

def main():
    usernames = [ line.strip() for line in readlines("usernames.txt") if line.strip() ]
    get_clips(usernames)

if __name__ == "__main__":
    with handler():
        main()
