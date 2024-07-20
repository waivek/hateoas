

# from colorama import Fore
import threading
import time
import sys
from enum import Enum
import os
import os.path
import json
import platform
from datetime import datetime
from waivek import Timer
from waivek import write, read, rel2abs
from waivek import Code
timer = Timer()
from waivek import ic, ib
from dbutils import Connection
import requests
from requests_ip_rotator import ApiGateway
ic, ib, Code

class Config:

    def __init__(self, token):
        from waivek import Date
        self.token = token
        D = self.decode_token(token)
        self.client_id = D['client_id']
        self.device_id = D['device_id']
        self.client_ip = D['client_ip']
        self.exp = Date(D['exp']).timeago()
        self.is_bad_bot = D['is_bad_bot']

    def decode_token(self, token):
        import base64
        string = token.split(".")[-1]
        output_bytes = base64.urlsafe_b64decode(string + '=' * (-len(string) % 4))
        index = output_bytes.rfind(b'"}')+1
        output_bytes_slice = output_bytes[:index+1]
        D = {}
        try:
            output_string = output_bytes_slice.decode("utf-8")
            D = json.loads(output_string)
        except Exception as e:
            error = e
            print("Error Token:")
            print(token)
            breakpoint()
        return D

    def print(self):
        D = {
            "token": self.token,
            "client_id": self.client_id,
            "device_id": self.device_id,
            "client_ip": self.client_ip,
            "exp": self.exp,
            "is_bad_bot": self.is_bad_bot
        }
        ic(D)


token = "v4.public.eyJjbGllbnRfaWQiOiJraW1uZTc4a3gzbmN4NmJyZ280bXY2d2tpNWgxa28iLCJjbGllbnRfaXAiOiI0OS4zNi4xNzkuNDciLCJkZXZpY2VfaWQiOiJmVm5xRk1JalVwOGc4VWFZWXVQVEVueUdDSEo0bHNFMSIsImV4cCI6IjIwMjMtMDctMDlUMDQ6MjQ6NTVaIiwiaWF0IjoiMjAyMy0wNy0wOFQxMjoyNDo1NVoiLCJpc19iYWRfYm90IjoiZmFsc2UiLCJpc3MiOiJUd2l0Y2ggQ2xpZW50IEludGVncml0eSIsIm5iZiI6IjIwMjMtMDctMDhUMTI6MjQ6NTVaIiwidXNlcl9pZCI6IiJ9gz4bxlI660pAcCI-_MeAiYq4Fh4q8UQDHwgS80YRjDdiWt9c0EdIOJRCDlWYRCOOMzRL2BZJSqwhmZTjKDHoBQ"
token = "v4.public.eyJjbGllbnRfaWQiOiJraW1uZTc4a3gzbmN4NmJyZ280bXY2d2tpNWgxa28iLCJjbGllbnRfaXAiOiI0OS4zNi4xNzcuMjQxIiwiZGV2aWNlX2lkIjoiRzZnWmZFZ3Y2YXdoNHMwd09ZanlkTVkyekZHUGxjYmQiLCJleHAiOiIyMDIzLTA3LTExVDA2OjAxOjM3WiIsImlhdCI6IjIwMjMtMDctMTBUMTQ6MDE6MzdaIiwiaXNfYmFkX2JvdCI6InRydWUiLCJpc3MiOiJUd2l0Y2ggQ2xpZW50IEludGVncml0eSIsIm5iZiI6IjIwMjMtMDctMTBUMTQ6MDE6MzdaIiwidXNlcl9pZCI6IiJ9VRrQptvEwRyEs8Lqc3Ioh6qmy2P9lgsfJ4WIJHdvx8Az7bnvE-H_fm1BSaZtJWNYGhFPfuzgPVEK53mkWemCDg"
token = "v4.public.eyJjbGllbnRfaWQiOiJraW1uZTc4a3gzbmN4NmJyZ280bXY2d2tpNWgxa28iLCJjbGllbnRfaXAiOiI0OS4zNi4xNzcuMjQxIiwiZGV2aWNlX2lkIjoiWXRYM0d2N3BJVjhjS2dINlVsSVpvSEhtcnhKSTNpMkkiLCJleHAiOiIyMDIzLTA3LTExVDA3OjI3OjM5WiIsImlhdCI6IjIwMjMtMDctMTBUMTU6Mjc6MzlaIiwiaXNfYmFkX2JvdCI6InRydWUiLCJpc3MiOiJUd2l0Y2ggQ2xpZW50IEludGVncml0eSIsIm5iZiI6IjIwMjMtMDctMTBUMTU6Mjc6MzlaIiwidXNlcl9pZCI6IiJ98mpsKf7ZQr27cW_ETRVrR4d-tBBSZ1tSwXU_zRJFQ96JFHBYDFfzh6eIfsaSnoBNohkbFHUxgE4z8nVlPm-TDQ"
token_from_selenium = "v4.public.eyJjbGllbnRfaWQiOiJraW1uZTc4a3gzbmN4NmJyZ280bXY2d2tpNWgxa28iLCJjbGllbnRfaXAiOiI0OS4zNi4xNzcuMjQxIiwiZGV2aWNlX2lkIjoiRUZ1QXYyVW10TWZIN1M5VzhSMXU1a0ZYb2M1Q0JabTYiLCJleHAiOiIyMDIzLTA3LTExVDA4OjUyOjUzWiIsImlhdCI6IjIwMjMtMDctMTBUMTY6NTI6NTNaIiwiaXNfYmFkX2JvdCI6ImZhbHNlIiwiaXNzIjoiVHdpdGNoIENsaWVudCBJbnRlZ3JpdHkiLCJuYmYiOiIyMDIzLTA3LTEwVDE2OjUyOjUzWiIsInVzZXJfaWQiOiIifdQGn5dJWH8Xs0pfJLAvd5xRE35wpcyxyKK9nbvTc9wOLlyl7g3QizECNjVNPbdYs6iITxgK-Bni0CR7ns4howI"


CONFIG = Config(token_from_selenium)
CONFIG.print()
if CONFIG.is_bad_bot:
    ic(CONFIG.is_bad_bot)

progress_lock = threading.Lock()

def query(video_id):
    pass

def make_kraken_request(url):
    pass

def abbreviate(number):
    number_int = int(number)
    number_string = str(number_int)
    number_length = len(str(number_int))
    if number_int < 100:
        return number_string
    first_digit, second_digit, third_digit = number_string[0:3]
    abbreviation_dict = {
         1:  "",  2:  "",  3:  "",
         4: "k",  5: "k",  6: "k",
         7: "m",  8: "m",  9: "m",
        10: "b", 11: "b", 12: "b",
        13: "t", 14: "t", 15: "t"
    }
    letter = abbreviation_dict[number_length]
    abbr_string = None
    if number_length % 3 == 0:
        # first three digits
        abbr_string = f"{first_digit}{second_digit}{third_digit}{letter}"
    if number_length % 3 == 2:
        # first two digits, period, next digit
        abbr_string = f"{first_digit}{second_digit}.{third_digit}{letter}"
    if number_length % 3 == 1:
        # first digit, period, next two digits
        abbr_string = f"{first_digit}.{second_digit}{third_digit}{letter}"

    return abbr_string

def smart_pad(current_value, max_value, fillchar='0'):
    number_of_digits = len(str(max_value))
    return str(current_value).rjust(number_of_digits, fillchar)


async def get(url, session, headers={}):
    global global_counter
    start_time = time.time()

    async with session.get(url, headers=headers) as response:
        json_content = await response.text()
        D = json.loads(json_content)
    end_time = time.time()
    return D

async def get_urls(urls, asyncio, aiohttp, headers={}):
    response_dictionaries = []
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        cors = [ get(url, session, headers) for url in urls ]
        response_dictionaries = await asyncio.gather(*cors)


    return response_dictionaries

class Status(Enum):
    ADVANCING = 1
    STOPPED = 2

class Block:
    def get_unique_end_comment(self, D):
        reversed_comments = list(reversed(D["comments"]))
        unique_end_comment = None
        for c1, c2, c3 in zip(reversed_comments, reversed_comments[1:], reversed_comments[2:]):
            p1 = c1["content_offset_seconds"]
            p2 = c2["content_offset_seconds"]
            p3 = c3["content_offset_seconds"]
            if p1 != p2 and p2 != p3:
                unique_end_comment = c2
                break
        # Assert: unique_end_comment != None {{{
        if unique_end_comment == None:
            error_string = Code.RED+"ERROR:"
            video_id = D["comments"][0]["content_id"]
            print()
            print("  {e} unique_end_comment == None. This mean’s that ALL the comments have the exact same 'content_offset_seconds'".format(e=error_string))
            print("  offset: {o}, video_id: {v}".format(o=self.offset, v=video_id))
            print()
            return
        # }}}
        return unique_end_comment

    def __init__(self, D, offset):
        self.comments = D["comments"]
        self.offset = offset
        self.real_offset = self.comments[0]["content_offset_seconds"]
        self.left = self.real_offset
        self.right = self.comments[-1]["content_offset_seconds"]
        self.unique_end_comment = self.get_unique_end_comment(D)
        self.cursor_next = D.get("_next")
        self.cursor_prev = D.get("_prev")
        self.status = Status.ADVANCING

    def add_dict(self, D):
        self.comments = self.comments + D["comments"]
        self.right = self.comments[-1]["content_offset_seconds"]
        self.unique_end_comment = self.get_unique_end_comment(D)
        self.cursor_next = D.get("_next")
        return self

    def pd_dict(self):
        assert self.unique_end_comment
        return {
            "real_offset" : self.real_offset,
            "unique_end"  : self.unique_end_comment["content_offset_seconds"],
            "comments"    : len(self.comments),
            "status"      : self.status
        }

    def __str__(self):
        assert self.unique_end_comment
        r = Code.GREEN+"%.2f" % self.real_offset
        u = Code.GREEN+"%.2f" % self.unique_end_comment["content_offset_seconds"]
        l =  "%d" % len(self.comments)
        return "Block: real_offset={r} unique_end={u} | {l} comments {s}".format(r=r, u=u, l=l, s=str(self.status))

    def __repr__(self):
        return str(self)

def update_status(blocks):

    # Handle last block
    if blocks[-1].cursor_next == None:
        blocks[-1].status = Status.STOPPED

    for i, (block, next_block) in enumerate(zip(blocks, blocks[1:])):
        block_end = block.unique_end_comment["content_offset_seconds"]
        next_real_offset = next_block.real_offset
        if block_end > next_real_offset:

            common_id_candidate = block.unique_end_comment["_id"]
            for comment in next_block.comments:
                if comment["content_offset_seconds"] > block_end:
                    break
                if comment["_id"] == common_id_candidate: # Verify that unique_end_comment appears in next_block to allow stitching
                    blocks[i].status = Status.STOPPED
                

    return blocks

# Used in chat_async AND chat_test_suite
def to_url(video_id, cursor_or_offset):
    url = None
    if type(cursor_or_offset) == float or type(cursor_or_offset) == int or cursor_or_offset.replace(".", "").isnumeric():
        offset = cursor_or_offset
        url = "https://api.twitch.tv/v5/videos/{video_id}/comments?content_offset_seconds={offset}".format(video_id=video_id, offset=offset)
    else:
        cursor = cursor_or_offset
        url = "https://api.twitch.tv/v5/videos/{video_id}/comments?cursor={cursor}".format(video_id=video_id, cursor=cursor)
    return url

def get_duration(video_id):
    duration_D = {'2120649324': 34242, '906027344': 43412.0, '952713884': 22776.0, '907555796': 40208.0, '917390403': 24820.0, '986329890': 44362.0, '987201168': 22780.0, '993650817': 30026.0, '1020137332': 14962.0, '1165771781': 27210.0, '1168307633': 28816.0, '1163658797': 73372.0, '1171217788': 90.0}

    if duration_D.get(video_id):
        video_duration = duration_D[video_id]
    else:
        # video_duration = float(query(video_id)["duration_seconds"])
        connection = Connection("data/videos.db")
        cursor = connection.execute("SELECT duration FROM videos WHERE id = ?;", (video_id,))
        video_duration = int(cursor.fetchone()[0])
        # print(Code.RED + f", '{video_id}': {video_duration}")
    return video_duration

def print_chat_async_oneliner(blocks, duration, request_count, start_time):
    # TODO: handle xchocobars case where there are contained/redundant blocks where next block is completely contained in current block
    elapsed_str = time.time()
    completed_block_count = len([block for block in blocks if block.status == Status.STOPPED])
    advancing_block_count = len([block for block in blocks if block.status == Status.ADVANCING])
    extra_seconds = [ pair.right-next_pair.left for pair, next_pair in zip(blocks, blocks[1:]) if pair.right > next_pair.left ]
    last_block_extra_seconds = 0 if blocks[-1].right < duration else duration - blocks[-1].right
    total_extra_seconds = sum(extra_seconds) + last_block_extra_seconds
    block_duration = sum(block.right-block.left for block in blocks)-total_extra_seconds
    fraction = block_duration / duration
    pct_str = "%6.2f" % (fraction * 100)
    elapsed_str = Code.GREEN+f"{elapsed_str:3.0f}s"
    oneliner_string = f"    [{pct_str}] {elapsed_str} Advancing: {advancing_block_count:3d}, Completed: {completed_block_count:3d}, Request Count: {request_count}"
    print(oneliner_string, end="\r")


def sort_offset_then_id(comment):
    return (comment["content_offset_seconds"], comment["_id"])

def chat_sync_dictionaries(video_id):
    url = to_url(video_id, 0)
    comments = []
    while True:
        D = make_kraken_request(url)
        assert D
        comments = comments + D["comments"]
        if not D.get("_next"):
            break
    return comments

def chat_async_dictionaries(video_id, duration=None):
    if duration and type(duration) == str:
        duration = int(duration)
    def pause_function(num):
        print()
        print(Code.RED + f"    [FAILED] Attempt {num}: ClientConnectorError")
        sleep_duration_seconds = 60
        for time_remaining in range(sleep_duration_seconds-1, -1, -1):
            info_string = Code.GREEN+smart_pad(time_remaining, sleep_duration_seconds)
            print(f"    Waiting {info_string}s before continuing", end="\r")
            time.sleep(1)
        print()

    from aiohttp.client_exceptions import ClientConnectorError
    import aiohttp
    import asyncio
    # TODO: Ensure this works on windows
    # if platform.system() == 'Windows':
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    start_time = time.time()
    BATCH_REQUEST_COUNT = 20
    # BATCH_REQUEST_COUNT = 25
    # BATCH_REQUEST_COUNT = 100
    video_duration = duration if duration else get_duration(video_id)
    if video_duration < 600:
        return chat_sync_dictionaries(video_id)
    slice_size = video_duration / BATCH_REQUEST_COUNT
    offsets = [ int(slice_size * i) for i in range(BATCH_REQUEST_COUNT) ]
    urls = [ to_url(video_id, offset) for offset in offsets ]
    # kraken_headers = { "Client-ID" : "4sx4524hdy15htgc37ob6fi3gat4rl", "Accept" : "application/vnd.twitchtv.v5+json" }
    kraken_headers = { "Client-ID" : "kimne78kx3ncx6brgo4mv6wki5h1ko", "Accept" : "application/vnd.twitchtv.v5+json" }
    dictionaries = asyncio.run(get_urls(urls, asyncio, aiohttp, headers=kraken_headers))
    blocks = None
    try:
        blocks = [ Block(D, offset) for D,offset in zip(dictionaries,offsets) ]
    except Exception as e:
        error = e
        breakpoint()
    assert blocks
    blocks = update_status(blocks)
    request_count = len(urls)
    print_chat_async_oneliner(blocks, video_duration, request_count, start_time)
    # return dictionaries


    while True:
        urls = []
        advance_indices = []
        for i, block in enumerate(blocks):
            if block.status == Status.STOPPED:
                continue
            cursor_next = block.cursor_next
            video_id_from_block = block.comments[0]["content_id"]
            advance_indices.append(i)
            urls.append(to_url(video_id_from_block, cursor_next))


        attempt_count = 3
        for i in range(attempt_count):
            try:
                dictionaries = asyncio.run(get_urls(urls, asyncio, aiohttp, headers=kraken_headers))
            except ClientConnectorError:
                attempt_number = i+1
                pause_function(attempt_number)
                dictionaries = []
            if dictionaries:
                break
        if not dictionaries:
            print()
            print(Code.RED + f"    [FAILED] {video_id} after {attempt_count} attempts.")
            breakpoint()
            return



        request_count = request_count + len(urls)
        for i,D in zip(advance_indices,dictionaries):
            try:
                blocks[i].add_dict(D)
            except Exception as e:
                error = e
                breakpoint()
        blocks = update_status(blocks)
        print_chat_async_oneliner(blocks, video_duration, request_count, start_time)
        advancing_block_count = len([ True for block in blocks if block.status == Status.ADVANCING ])
        if advancing_block_count == 0:
            break
    # def stitch(block1, block2) {{{
    def stitch(block1, block2):
        stitch_id = block1.unique_end_comment["_id"]
        block1_ids = [ comment["_id"] for comment in block1.comments ]
        block1_end_index = block1_ids.index(stitch_id)
        block2_ids = [ comment["_id"] for comment in block2.comments ]
        block2_start_index = block2_ids.index(stitch_id)
        stitched_block = block1
        stitched_comments = block1.comments[0:block1_end_index] + block2.comments[block2_start_index:]
        stitched_block.comments = stitched_comments
        stitched_block.right = block2.right
        stitched_block.unique_end_comment = block2.unique_end_comment
        stitched_block.cursor_next = block2.cursor_next
        return stitched_block
    # }}}

    print()

    # check if previous block contains current block 
    # we don’t check left as we have a guarantee that the left’s are always in increasing order
    redundant_blocks = [ current_block for previous_block, current_block in zip(blocks, blocks[1:]) if previous_block.right > current_block.right ]
    for redundant_block in redundant_blocks:
        blocks.remove(redundant_block)

    block_acc = blocks[0]
    for i, block in enumerate(blocks[1:]):
        try:
            block_acc = stitch(block_acc, block)
        except Exception as e:
            missing_comment_D = blocks[i].unique_end_comment
            assert missing_comment_D
            missing_id = missing_comment_D["_id"]
            missing_content_offset_seconds = missing_comment_D["content_offset_seconds"]
            error = e
            print(f"Error Index: {i}")
            print(f"blocks[{i}]: blocks[i]")
            print(f"blocks[{i+1}]: blocks[i+1]")
            print(f"Missing ID: {missing_id}; Missing Offset: {missing_content_offset_seconds}")
            breakpoint()
    block_acc.comments.sort(key=sort_offset_then_id)
    comment_dictionaries = block_acc.comments
    comment_count = len(comment_dictionaries)
    comment_count_abbr = Code.GREEN+f"[{abbreviate(comment_count)}]"
    print(f"    Comment Count: {comment_count} {comment_count_abbr}")
    print()
    return comment_dictionaries

def download_chat_1541650024():
    video_id = "1541650024"
    filename = f"temp-{video_id}.json"
    json_filepath = rel2abs(filename)
    dictionaries = chat_async_dictionaries(video_id, 19590)
    with open(json_filepath, "w") as f:
        json.dump(dictionaries, f, indent=4)
        print(json_filepath)

def color_filepath(filepath):
    import os.path
    dirname = Code.LIGHTBLACK_EX + os.path.dirname(filepath)
    basename = Code.LIGHTCYAN_EX + os.path.basename(filepath) 
    result = os.path.join(dirname, basename) 
    return result

def write_artifact(filename, obj):
    artifacts_directory = rel2abs("artifacts")
    os.makedirs(artifacts_directory, exist_ok=True)
    filepath = os.path.join(artifacts_directory, filename)
    filepath_colored = color_filepath(filepath)
    with open(filepath, "w") as f:
        json.dump(obj, f, indent=4)
        print(filepath_colored)

def upload_chat_artifact():
    now = datetime.now()
    date_string = f"{now:%Y-%m-%d %H:%M%S}"
    video_pairs = json.loads(sys.argv[1])
    for video_id, video_duration in video_pairs:
        D = { "video_id": video_id, "video_duration": video_duration }
        dictionaries = chat_async_dictionaries(video_id, video_duration)
        write_artifact(f"{video_id}.json", dictionaries)

def print_args():
    video_pairs = json.loads(sys.argv[1])
    for video_id, video_duration in video_pairs:
        print(f"ID: {video_id}, Duration: {video_duration}")
    write_artifact("action-args.json", video_pairs)

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


def comments_gql():
    import requests
    video_id = "1863704634"
    duration = 10349
    content_offset_seconds = 100
    headers = { 'Client-Id': 'kimne78kx3ncx6brgo4mv6wki5h1ko', }
    url = "https://gql.twitch.tv/gql"

    headers = { 'Client-Id': 'kimne78kx3ncx6brgo4mv6wki5h1ko', }

    one_op = get_data_D(video_id, 100)
    two_op = get_data_D(video_id, 1000)
    data = [
        one_op,
        two_op
    ]
    data_string = json.dumps(data)

    response = requests.post('https://gql.twitch.tv/gql', headers=headers, data=data_string)
    L = response.json()
    obj1 = L[0]
    obj2 = L[1]
    is_eq = obj1 == obj2
    ic(is_eq)
    print(response.status_code)


def get_session():
    import requests
    global CONFIG
    session = requests.Session()
    headers = { 
       'Client-Id': CONFIG.client_id, 
       'Client-Integrity': CONFIG.token,
        'X-Device-Id': CONFIG.device_id,
    }
    session.headers.update(headers)
    return session



session = None
def request_one_D(video_id, cursor_or_offset):
    global session
    duration = 10349
    D = get_data_D(video_id, cursor_or_offset)
    L = [ D ]
    data_string = json.dumps(D)
    if session is None:
        session = get_session()
    response = session.post('https://gql.twitch.tv/gql', data=data_string)
    # response = session.post('https://gql.twitch.tv/gql', headers=headers, data=data_string)
    # response = requests.post('https://gql.twitch.tv/gql', headers=headers, data=data_string)
    return response.json()

def get_D_oneliner(D, duration=None):
    from waivek import truncate
    from waivek import Timestamp

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
        string = f"{green_fg_ansi}{pct_str}{reset_ansi} [{first_offset_str} - {last_offset_str}] of {blue_fg_ansi}{duration_str}{reset_ansi} ({edge_count} Edges) hasNextPage:{has_next_page} cursor:{cursor}"
    else:
        string = f"[{first_offset_str} - {last_offset_str}] ({edge_count} Edges) hasNextPage:{has_next_page} cursor:{cursor}"
    return string

def get_integrity_token():
    import requests
    headers = { 'Client-Id': 'kimne78kx3ncx6brgo4mv6wki5h1ko', }
    response = requests.post('https://gql.twitch.tv/integrity', headers=headers)
    D = response.json()
    integrity_token = D['token']
    return integrity_token

def D_to_offsets(D):
    edges = D['edges']
    offsets = [ edge['node']['contentOffsetSeconds'] for edge in edges ]
    return offsets

def gql_is_valid():
    global session
    if session is None:
        session = get_session()
    D = {
        "operationName": "GetUserID",
        "variables": {
        "login": "starsmitten",
        "lookupType": "ACTIVE"
        },
    "extensions": {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": "bf6c594605caa0c63522f690156aa04bd434870bf963deb76668c381d16fcaa5"
            }
        }
    }
    data_string = json.dumps(D)

    response = session.post('https://gql.twitch.tv/gql', data=data_string)
    condition_1 = response.status_code == 200
    D = response.json()
    user_id = '61852275'
    condtion_2 = D['data']['user']['id'] == user_id
    if not condition_1:
        print("Failed: response.status_code != 200")
    if not condtion_2:
        print("Failed: user_id != 61852275")
    return condition_1 and condtion_2

def chat_gql_sync(video_id):
    path = f"data/offsets/{video_id}.json"
    if os.path.exists(path):
        offsets = read(path)
        return offsets
    from collections import Counter
    request_count = 0
    D = request_one_D(video_id, 0)
    request_count = request_count + 1
    D = D['data']['video']['comments']
    print(get_D_oneliner(D))
    offsets = D_to_offsets(D)

    while D['pageInfo']['hasNextPage']:
        cursor = D['edges'][-1]['cursor'] 

        D = request_one_D(video_id, cursor)
        request_count = request_count + 1
        if D['data']['video']['comments'] is None:
            ic(D)
            breakpoint()
        D = D['data']['video']['comments']
        print(get_D_oneliner(D))
        offsets = offsets + D_to_offsets(D)
    counts = Counter(offsets)
    counts_D = dict(counts)
    ic(request_count)
    ic(path)

    write(offsets, path)
    return offsets

def read_progress_json(video_id):
    data_path = rel2abs(f"data/chat_download_progress/{video_id}.json")
    if not os.path.exists(data_path):
        return { "progress": 0, "video_id": video_id, "status": "Not Started" }
    global progress_lock
    with progress_lock:
        D = read(data_path)
    return D

def write_progress_json(seconds_completed, total_seconds, video_id, status):
    path = f"data/chat_download_progress/{video_id}.json"
    percentage_completion = seconds_completed / total_seconds
    D = {
        "progress": percentage_completion,
        "video_id": video_id,
        "status": status
    }
    global progress_lock
    with progress_lock:
        write(D, path)

def chat_gql_sync_ip_rotation_offset(video_id):
    # offset < duration is bad practice but no choice for non cursor fetch
    path = f"data/offsets/{video_id}.json"
    temp_path = f"data/offsets/temp-{video_id}.json"

    if os.path.exists(rel2abs(path)):
        offsets = read(path)
        print("[EXISTS] " + (Code.LIGHTCYAN_EX + path))
        return offsets
    duration = get_video_duration_by_id_from_database(video_id)
    domain = "https://gql.twitch.tv"
    url = "https://gql.twitch.tv/gql"
    gateway = ApiGateway(domain)
    endpoints = gateway.start()
    
    from requests.adapters import HTTPAdapter
    # import maxretryerror
    from urllib3.exceptions import MaxRetryError, ConnectionError
    from urllib3.util.retry import Retry
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
    offset = 0
    comments = []
    request_count = 0
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
        first_offset = D['edges'][0]['node']['contentOffsetSeconds']
        last_offset = D['edges'][-1]['node']['contentOffsetSeconds']
        has_next_page = D['pageInfo']['hasNextPage'] 
        # HACK FOR SMALL WINDOWS TO PREVENT REPETITION, ALSO CAUSED BY GOING BY OFFSET INSTEAD OF CURSOR
        if offset >= last_offset:
            offset = offset + 1
        else:
            offset = last_offset
        for edge in D['edges']:
            id = edge['node']['id']
            content_offset = edge['node']['contentOffsetSeconds']
            comments.append((id, content_offset))
    ic(len(comments))
    comments = list(set(comments))
    dictionaries = [ {"id": id, "offset": offset} for id, offset in comments ]
    dictionaries.sort(key=lambda x: x['offset'])
    ic(len(dictionaries))
    ic(request_count)
    offsets = [ dictionary['offset'] for dictionary in dictionaries ]
    write(offsets, path)
    print("[WRITE] " + (Code.LIGHTCYAN_EX + path))
    write_progress_json(duration, duration, video_id, "Completed")
    print("[WRITE] " + (Code.LIGHTCYAN_EX + path))

    gateway.shutdown()
    return offsets


def generate_token():
    # import undetected_chromedriver as uc
    video_id = "1863704634"
    url = f"https://www.twitch.tv/videos/{video_id}"

    # from seleniumwire import webdriver
    # from selenium.webdriver.chrome.options import Options
    # options = Options()
    # # options.add_argument('--headless')
    # driver = webdriver.Chrome(options=options)
    import seleniumwire.undetected_chromedriver as uc
    # from selenium.webdriver.common.proxy import Proxy, ProxyType
    capabilities = uc.webdriver.DesiredCapabilities.CHROME
    options = uc.ChromeOptions()
    # options.headless = False
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    driver = uc.Chrome(options=options, capabilities=capabilities)

    # import undetected_chromedriver as uc
    # options = uc.ChromeOptions()
    # options.headless = False
    # driver = uc.Chrome(use_subprocess=True, options=options, enable_cdp_events=True)

    # from waivek import pack
    # requests = []
    # table = []
    # all_reqs = []
    # def print_function(req):
    #     all_reqs.append(req)
    #     ic(len(all_reqs))
    #     url = req['params']['documentURL']
    #     headers = req['params']['request']['headers']
    #     method = req['params']['request']['method'] 
    #     D = pack(url, headers, method, req)
    #     
    #     if 'gql' in url:
    #         requests.append(req)
    #         table.append(D)
    # # driver.set_page_load_timeout(20)
    # driver.add_cdp_listener("Network.requestWillBeSent", print_function)

    driver.get(url)
    # reqs = requests
    wait_time_seconds = 120
    selected_config = None
    for i in range(wait_time_seconds):
        time.sleep(1)
        print(f"Time Elapsed: {i}")
        A = [ req for req in driver.requests if "gql" in req.url ]
        ic(len(A))
        B = [ dict(req.headers) for req in A ]
        ic(len(B))
        C = [ var for var in B if "Client-Integrity" in var ]
        ic(len(C))
        if len(C) > 0:
            dictionaries = C
            tokens = [ D["Client-Integrity"] for D in dictionaries ]
            tokens = list(set(tokens))
            configs = [ Config(token) for token in tokens ]
            is_bad_bot_values = [ config.is_bad_bot for config in configs ]
            ic(is_bad_bot_values)
            if 'false' in is_bad_bot_values:
                index = is_bad_bot_values.index('false')
                selected_config = configs[index]
                break

                
            # D = C[0]
            # token = D["Client-Integrity"]
            # sample_config = Config(token)
            # ic(token)
            # sample_config.print()

        else:
            pass
            # print("TOKEN NOT FOUND")


    assert selected_config
    selected_config.print()
    breakpoint()
    driver.close()

def bye():
    return "BYE"

def main():
    # dogw()
    # return
    # generate_token()
    # return
    # # is_valid = gql_is_valid()
    # # ic(is_valid)

    video_id = "1863704634"
    video_id = "1863493317"
    video_id = "1882272513"
    video_id = "1885190407"
    video_id = "1903569158"
    video_id = "2037410873"
    video_id = "2068824410"

    video_id = "2120649324"
    video_id = "2199695545"
    chat_gql_sync_ip_rotation_offset(video_id)
    return
    # path_to_delete = rel2abs(f"data/offsets/{video_id}.json")
    # if os.path.exists(path_to_delete):
    #     os.remove(path_to_delete)


    timer.start("chat_gql_sync")
    chat_gql_sync(video_id)
    timer.print("chat_gql_sync")
    return

    # if platform.system() == 'Windows':
    #     from colorama import init
    #     init(convert=True)

    if len(sys.argv) == 2:
        # print_args()
        upload_chat_artifact()


if __name__ == "__main__":
    from waivek import handler
    with handler():
        main()

