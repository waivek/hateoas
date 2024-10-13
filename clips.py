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
    user_ids = helix_name2id([username])
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
    cursor.execute("DROP TABLE IF EXISTS clips;")
    create_table_if_not_exists(cursor)
    for resp in responses:
        table = resp['data']
        for row in table:
            created_at_utc_string = row["created_at"] # Format: 2023-07-28T16:38:57Z
            created_at_utc = datetime.strptime(created_at_utc_string, "%Y-%m-%dT%H:%M:%SZ")
            created_at_epoch = int(created_at_utc.timestamp())
            row["duration"] = int(row["duration"])
            row["created_at_epoch"] = created_at_epoch
        insert_dictionaries(cursor, 'clips', table)
    connection.commit()
    query = "SELECT * FROM clips LIMIT 5"
    cursor.execute(query)
    rows = cursor.fetchall()
    table = [ dict(row) for row in rows ]
    ic(table)

def main():
    usernames = [ line.strip() for line in readlines("usernames.txt") ]
    get_clips(usernames)

main()
# if __name__ == "__main__":
#     with handler():
#         main()
