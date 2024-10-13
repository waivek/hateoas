
from waivek import Timer   # Single Use
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
from waivek import unpack
import isodate
import requests

def helix_name2id(usernames):
    parameter_string = "?login="+"&login=".join(usernames)
    url = f"https://api.twitch.tv/helix/users{parameter_string}"
    client_id, oath_token = get_helix_client_id_and_oath_token()
    headers = { "Client-ID" : client_id, "Authorization" : "Bearer " + oath_token }
    response = requests.get(url, headers=headers)
    json_D = response.json()
    unsynchronized_dictionaries = json_D["data"] # unsynced because dictionaries is not in same order as new_usernames
    username2user_id =  { D["login"]: D["id"]  for D in unsynchronized_dictionaries }
    user_id2username = { v: k for k, v in username2user_id.items() }
    user_ids = [ username2user_id[username] for username in usernames ]
    return user_ids

class Paths:
    def __init__(self):
        self.db_path = rel2abs('data/videos.db')
        self.schema_path = rel2abs('schema/videos.sql')

paths = Paths()


def get_videos_url(username):
    user_ids = helix_name2id([username])
    user_id = user_ids[0]
    videos_url = "https://api.twitch.tv/helix/videos?user_id={user_id}".format(user_id=user_id)
    return videos_url

def twitch_duration_string_to_seconds(duration_string):
    from waivek import Timestamp
    if 'm' not in duration_string:
        duration_string = '00m' + duration_string
    if 'h' not in duration_string:
        duration_string = '00h' + duration_string
    seconds = Timestamp(duration_string).seconds
    return seconds



def create_table_if_not_exists(cursor):
    table_name = "videos"
    table_exists = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'".format(table_name=table_name)).fetchone()
    if not table_exists:
        schema_sql_lines = readlines(paths.schema_path)
        schema_sql = "\n".join(schema_sql_lines)
        cursor.executescript(schema_sql)
        print(f"Creating table '{table_name}'")
        print(f"Executing schema '{paths.schema_path}'")

def get_live_stream_ids(usernames):
    user_ids = helix_name2id(usernames)
    joined_user_ids = "&user_id=".join(user_ids)
    streams_url = f"https://api.twitch.tv/helix/streams?user_id={joined_user_ids}"
    client_id, oath_token = get_helix_client_id_and_oath_token()
    headers = { "Client-ID" : client_id, "Authorization" : "Bearer " + oath_token }
    responses = aget([streams_url], cache=False, url2header=lambda url:headers)
    streams = responses[0]['data']
    stream_ids = [ stream['id'] for stream in streams ]
    return stream_ids

def get_videos(usernames):
    from datetime import timedelta
    from datetime import datetime
    connection = db_init(paths.db_path)
    cursor = connection.cursor()
    cursor.execute("DROP TABLE IF EXISTS videos;")
    create_table_if_not_exists(cursor)
    client_id, oath_token = get_helix_client_id_and_oath_token()
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    urls = [ get_videos_url(username) for username in usernames ]
    headers = { "Client-ID" : client_id, "Authorization" : "Bearer " + oath_token }
    responses = aget(urls, cache=False, url2header=lambda url:headers)
    live_stream_ids = get_live_stream_ids(usernames)
    insert_table = []
    for resp in responses:
        table = resp['data']
        for row in table:
            created_at, duration, stream_id, thumbnail_url, user_name = unpack(row)
            if stream_id in live_stream_ids:
                print(Code.LIGHTBLUE_EX + f"Skipping live stream {stream_id} for user {user_name}")
                if "_404/" in thumbnail_url:
                    print(Code.RED + "... It also has a 404 thumbnail")
                continue
            if "_404/" in thumbnail_url:
                print(Code.RED + "Found 404 thumbnail, skipping")
                continue
            created_at_utc_string = row["created_at"] # Format: 2023-07-28T16:38:57Z
            created_at_epoch = int(isodate.parse_datetime(created_at_utc_string).timestamp())
            duration = twitch_duration_string_to_seconds(duration)
            row["duration"] = duration
            row["created_at_epoch"] = int(created_at_epoch)
            row["is_youtube"] = 0
            insert_table.append(row)
    insert_dictionaries(cursor, 'videos', insert_table)
    connection.commit()
    query = "SELECT * FROM videos LIMIT 5"
    cursor.execute(query)
    rows = cursor.fetchall()
    table = [ dict(row) for row in rows ]
    ic(table)

def main():
    usernames = [ line.strip() for line in readlines("usernames.txt") ]
    get_videos(usernames)

if __name__ == "__main__":
    with handler():
        main()
