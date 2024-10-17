import diskcache as dc
import requests
from waivek import rel2abs
from auth import get_helix_client_id_and_oath_token

def query_user_ids(usernames) -> list[str]:

    cache = dc.Cache(rel2abs("data/username2userid_cache"))
    new_usernames = [ username for username in usernames if username not in cache ]

    if new_usernames:
        print(f"[query_user_ids] Found new usernames: {','.join(new_usernames)}")
        parameter_string = "?login="+"&login=".join(new_usernames)
        url = f"https://api.twitch.tv/helix/users{parameter_string}"
        client_id, oath_token = get_helix_client_id_and_oath_token()
        response = requests.get(url, headers={ "Client-ID" : client_id, "Authorization" : "Bearer " + oath_token })
        json_D = response.json()
        unsynchronized_dictionaries = json_D["data"] # unsynced because dictionaries is not in same order as new_usernames
        name_id_pairs = [ (D["login"], D["id"]) for D in unsynchronized_dictionaries ]
        for username, user_id in name_id_pairs:
            cache.set(username, user_id)

    user_ids = [ cache.get(username) for username in usernames ]
    return user_ids
