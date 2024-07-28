import os
import json
import time
import gzip

from waivek import rel2abs, read, write, Code, ic, truncate, Timestamp, Timer
timer = Timer()
from worker_utils import has_chat_part_file, is_chat_downloaded, get_chat_downloads_folder

from requests_ip_rotator import ApiGateway
import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import MaxRetryError, ConnectionError
from urllib3.util.retry import Retry
from get_gateway import get_gateway_with_caching

from chat_part_file_utils import append_data_to_part_file, get_last_offset_from_part_file, part_file_to_json


def get_D_oneliner(D, duration=None):

    first_offset = D['edges'][0]['node']['contentOffsetSeconds']
    last_offset = D['edges'][-1]['node']['contentOffsetSeconds']
    edge_count = len(D['edges'])
    has_next_page = D['pageInfo']['hasNextPage'] 
    cursor = truncate(D['edges'][-1]['cursor'], 80)
    first_offset_str = Timestamp(first_offset).timestamp
    last_offset_str = Timestamp(last_offset).timestamp
    green_bg_black_fg_ansi = '\x1b[42;30m'
    green_fg_ansi = '\x1b[32m'
    reset_ansi = '\x1b[0m'
    blue_fg_ansi = '\x1b[34m'
    if duration:
        pct = first_offset / duration * 100
        pct_str = f"{pct:.2f}%".rjust(len("100.00%"))
        duration_str = Timestamp(duration).hh_mm_ss
        # string = f"{pct:.2f}% [{first_offset_str}  {last_offset_str}] ({edge_count} Edges) hasNextPage:{has_next_page} cursor:{cursor}"
        string = f"{green_fg_ansi}{pct_str}{reset_ansi} [{first_offset_str} - {last_offset_str}] of {blue_fg_ansi}{duration_str}{reset_ansi} ({edge_count} Edges) hasNextPage:{has_next_page}"
    else:
        string = f"[{first_offset_str} - {last_offset_str}] ({edge_count} Edges) hasNextPage:{has_next_page}"
    return string

def get_data_D(video_id, cursor_or_offset):
    if type(cursor_or_offset) is int or cursor_or_offset.isdigit():
        key = "contentOffsetSeconds"
    else:
        key = "cursor"
    D = {
        "operationName": "VideoCommentsByOffsetOrCursor",
        "variables": {
            "videoID": video_id,
            key: cursor_or_offset,
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a"
            }
        }
    }
    return D

def get_video_duration_by_id_from_database(video_id):
    from waivek import db_init
    from waivek import Timestamp

    connection = db_init("data/videos.db")
    cursor = connection.cursor()
    cursor.execute("SELECT duration FROM videos WHERE id = ?;", (video_id,))
    duration_int, = cursor.fetchone()
    duration_string = str(duration_int)
    if 'm' not in duration_string:
        duration_string = '00m' + duration_string
    if 'h' not in duration_string:
        duration_string = '00h' + duration_string
    seconds = Timestamp(duration_string).seconds
    return seconds



def chat_gql_sync_ip_rotation_offset_resumable(video_id) -> None:
    if is_chat_downloaded(video_id):
        print("[SKIP] " + (Code.LIGHTCYAN_EX + video_id))
        return

    function_name = "chat_gql_sync_ip_rotation_offset_resumable"
    # offset < duration is bad practice but no choice for non cursor fetch

    folder = get_chat_downloads_folder()
    if not os.path.exists(folder):
        os.makedirs(folder)
    part_path = os.path.join(folder, f"{video_id}.json.part")
    json_zip_path = os.path.join(folder, f"{video_id}.json.gz")

    # if has_chat_part_file(video_id) and chat_part_file_has_data(video_id):
    #     print("[RESUME] " + (Code.LIGHTCYAN_EX + part_path))
    #     dicts = read(part_path)
    #     D = dicts[-1]
    #     offset = D['edges'][-1]['node']['contentOffsetSeconds']
    # else:
    #     # init the part file with an empty list
    #     write([], part_path)
    #     print("[START] " + (Code.LIGHTCYAN_EX + part_path))
    #     offset = 0

    if not os.path.exists(part_path) or os.stat(part_path).st_size == 0:
        with open(part_path, 'w') as f:
            f.write('')
        offset = 0
        print("[START] " + (Code.LIGHTCYAN_EX + part_path))
    else:
        offset = get_last_offset_from_part_file(part_path)
        print("[RESUME] " + (Code.LIGHTCYAN_EX + part_path))

    duration = get_video_duration_by_id_from_database(video_id)
    domain = "https://gql.twitch.tv"
    url = "https://gql.twitch.tv/gql"
    gateway = get_gateway_with_caching(domain)
    
    retry_strategy = Retry(
        total=5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
        backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)

    session = requests.Session()
    session.mount(url, adapter)
    session.mount(url, gateway)
    headers = { 'Client-Id': "kimne78kx3ncx6brgo4mv6wki5h1ko" }
    session.headers.update(headers)

    has_next_page = True


    request_count = 0
    print(f"[{function_name}] {video_id}")

    # touch {part_path}
    while has_next_page and offset < duration:
        D = get_data_D(video_id, offset)
        data_string = json.dumps(D)
        attempt_count = 3
        response = None
        while attempt_count > 0:
            try:
                response = session.post(url, data_string)
            except Exception as e:
                error = e
                attempt_count = attempt_count - 1
                print("MaxRetryError, Retrying in 5 seconds")
                time.sleep(5)
                continue
            if response.status_code == 200:
                break
        request_count = request_count + 1

        assert response
        D = response.json()
        D = D['data']['video']['comments']
        print(get_D_oneliner(D, duration))
        # dicts.append(D)
        append_data_to_part_file(part_path, D)


        first_offset = D['edges'][0]['node']['contentOffsetSeconds']
        last_offset = D['edges'][-1]['node']['contentOffsetSeconds']
        # if last_offset > 600:
        #     break # for debugging
        has_next_page = D['pageInfo']['hasNextPage'] 
        # HACK FOR SMALL WINDOWS TO PREVENT REPETITION, ALSO CAUSED BY GOING BY OFFSET INSTEAD OF CURSOR
        if offset >= last_offset:
            offset = offset + 1
        else:
            offset = last_offset
    timer.start("part_file_to_json")
    L = part_file_to_json(part_path)
    print("[WRITE] " + (Code.LIGHTCYAN_EX + json_zip_path))
    timer.print("part_file_to_json")
    with gzip.open(json_zip_path, 'wt') as f:
        json.dump(L, f, indent=4)
    os.remove(part_path)
    ic(request_count)
    # gateway.shutdown()

def get_chat_offsets_of_downloaded_video(video_id):
    if not is_chat_downloaded(video_id):
        raise Exception(f"Chat not downloaded for {video_id}")


    folder = get_chat_downloads_folder()
    json_path = os.path.join(folder, f"{video_id}.json.gz")
    comments = []
    # dicts = read(json_path)
    with gzip.open(json_path, 'rt') as f:
        dicts = json.load(f)
    for D in dicts:
        for edge in D['edges']:
            id = edge['node']['id']
            content_offset = edge['node']['contentOffsetSeconds']
            comments.append((id, content_offset))
    ic(len(comments))
    comments = list(set(comments))
    dictionaries = [ {"id": id, "offset": offset} for id, offset in comments ]
    dictionaries.sort(key=lambda x: x['offset'])
    ic(len(dictionaries))
    offsets = [ dictionary['offset'] for dictionary in dictionaries ]
    print("Done.")
    return offsets
    # path = f"data/offsets/{video_id}.json"
    # write(offsets, path)
    # print("[WRITE] " + (Code.LIGHTCYAN_EX + path))


def main():
    video_id = "2199695545"
    # chat_gql_sync_ip_rotation_offset_resumable(video_id)
    timer.start("get_chat_offsets_of_downloaded_video")
    offsets = get_chat_offsets_of_downloaded_video(video_id)
    timer.print("get_chat_offsets_of_downloaded_video")


if __name__ == "__main__":
    main()
