from waivek import Connection, Timer, readlines, truncate

from filter_out_existing_records import filter_out_existing_records   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
from auth import get_helix_client_id_and_oath_token
from helix import Helix
from models.model_pydantic_games import Game
import requests

clips_connection = Connection("data/clips.db")
games_connection = Connection("data/games.db")

def create_table_if_not_exists(cursor, table_name, schema_path):
    table_exists = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'".format(table_name=table_name)).fetchone()
    if not table_exists:
        schema_sql_lines = readlines(schema_path)
        schema_sql = "\n".join(schema_sql_lines)
        cursor.executescript(schema_sql)
        print(f"Creating table '{table_name}'")
        print(f"Executing schema '{schema_path}'")

def foo(session):
    url = "https://api.twitch.tv/helix/games?id=33214"
    response = session.get(url)
    data = response.json()
    print(data)

def main():
    helix = Helix()
    cursor = clips_connection.cursor()
    cursor.execute("SELECT DISTINCT game_id FROM clips WHERE game_id IS NOT NULL")
    cursor = games_connection.cursor()
    create_table_if_not_exists(cursor, "games", rel2abs("schema/games.sql"))
    cursor.execute("SELECT COUNT(*) FROM games")
    count_before = cursor.fetchone()[0]
    game_ids = [ game_id for game_id, in cursor.fetchall() ]
    game_ids = filter_out_existing_records(cursor, game_ids)

    window_size = 100
    base_url = "https://api.twitch.tv/helix/games"
    games = []
    table = []
    for i in range(0, len(game_ids), window_size):
        game_ids_slice = game_ids[i:i+window_size]
        game_ids_str = "&id=".join([str(game_id) for game_id in game_ids_slice])
        url = f"{base_url}?id={game_ids_str}"
        print(f"GET {truncate(url, 80)}")
        # print(f"GET {url}")
        response = helix.get(url)
        data = response.json()
        game_objects = data["data"]
        for game_object in game_objects:
            game = Game(**game_object)
            table.append(game_object)
            games.append(game)

        print(f"Queried {len(game_ids_slice)} games, Found {len(game_objects)}")
    # CREATE TABLE games (id TEXT NOT NULL PRIMARY KEY, name TEXT NOT NULL, box_art_url TEXT NOT NULL, igdb_id TEXT NOT NULL) STRICT;
    if len(games) != 0:
        print(f"Inserting {len(games)} games into the database")
        cursor.executemany("INSERT INTO games (id, name, box_art_url, igdb_id) VALUES (:id, :name, :box_art_url, :igdb_id)", table)
        games_connection.commit()
    print(f"New Game ID's = {len(game_ids)}")
    cursor.execute("SELECT COUNT(*) FROM games")
    count_after = cursor.fetchone()[0]
    print(f"Before = {count_before}, After = {count_after}, Diff = {count_after - count_before}")

if __name__ == "__main__":
    with handler():
        main()
