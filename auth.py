# DUPE of ~/Twitch/coffee-vps/code/auth.py
from waivek import db_init
from time import time
import json

def table_exists(cursor, table_name):
    statement = f"SELECT * FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    D = cursor.execute(statement).fetchall()
    return True if D else False

def make_oath_request(client_id, client_secret):
    # https://dev.twitch.tv/console/apps/4sx4524hdy15htgc37ob6fi3gat4rl
    import requests
    url_template = "https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
    url = url_template.format(client_id=client_id, client_secret=client_secret)
    x = requests.post(url)
    response_D = json.loads(x.text)
    return response_D

def get_oath_token(client_id, client_secret):
    connection = db_init("data/auth.db")
    cursor = connection.cursor()
    table_name = "helix_auth"
    if table_exists(cursor, table_name):
        row = cursor.execute(f"SELECT oath_token, expires_epoch FROM {table_name};").fetchone()
    else:
        row = None
    if row and time() < row["expires_epoch"]:
        return row["oath_token"]
    cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
    cursor.execute(f"CREATE TABLE {table_name} (oath_token TEXT, expires_epoch INTEGER);")
    response_D = make_oath_request(client_id, client_secret)
    oath_token = response_D["access_token"]
    expires_epoch = time() + response_D["expires_in"]
    cursor.execute(f"INSERT INTO {table_name} VALUES (?, ?);", [ oath_token, expires_epoch ])
    connection.commit()
    row = cursor.execute(f"SELECT oath_token, expires_epoch FROM {table_name};").fetchone()
    return row["oath_token"]

def get_helix_client_id_and_oath_token():
    helix_client_id = "4sx4524hdy15htgc37ob6fi3gat4rl"
    helix_client_secret = "7o1gsem1zfxcawvcpl8isqmlegnmwe"
    helix_oath_token = get_oath_token(helix_client_id, helix_client_secret)
    return (helix_client_id, helix_oath_token)

