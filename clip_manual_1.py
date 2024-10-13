import time
from waivek import Timer   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
import argparse
import requests
from auth import get_helix_client_id_and_oath_token
import dateutil.parser
from waivek import Timestamp
from datetime import datetime

class SetHTMLStatus():
    def __init__(self, total):
        self.start_time = time.time()
        self.total = total
        self.counter = 0
    def set_html_status(self, text):
        print(f"[{self.counter+1}/{self.total}] [{time.time() - self.start_time:.2f}s] {text}")
        self.counter += 1

def usernames_to_user_id(usernames):
    parameter_string = "?login="+"&login=".join(usernames)
    url = f"https://api.twitch.tv/helix/users{parameter_string}"
    client_id, oauth_token = get_helix_client_id_and_oath_token()
    response = requests.get(url, headers={"Client-ID": client_id, "Authorization": "Bearer " + oauth_token})
    json_D = response.json()
    unsynchronized_dictionaries = json_D["data"] # unsynced because dictionaries is not in same order as new_usernames
    username2user_id =  { D["login"]: D["id"]  for D in unsynchronized_dictionaries }
    user_id2username = { v: k for k, v in username2user_id.items() }
    user_ids = [ username2user_id[username] for username in usernames ]
    return user_ids


def twitch_duration_string_to_seconds(duration_string):
    if 'm' not in duration_string:
        duration_string = '00m' + duration_string
    if 'h' not in duration_string:
        duration_string = '00h' + duration_string
    seconds = Timestamp(duration_string).seconds
    return seconds

def manual_clip_to_synced_vods(clip_id, users) -> dict:
    """
    Queries only the first 20 most recent videos of each user
    No DB calls involved for video queries as we are assuming that 
        [1] user is new and not indexed in videos.db
        or
        [2] the clip is from a recent VOD that is not in videos.db
    """

    status = SetHTMLStatus(2 + len(users))
    start_time = time.time()
    user_ids = usernames_to_user_id(users)


    client_id, oauth_token = get_helix_client_id_and_oath_token()
    clips_url = "https://api.twitch.tv/helix/clips?id=" + clip_id
    headers = {
        "Client-ID": client_id,
        "Authorization": "Bearer " + oauth_token
    }
    status.set_html_status(f"GET {clips_url}")
    response = requests.get(clips_url, headers=headers).json()
    clip = response["data"][0]
    source_video_id = clip["video_id"]
    videos_url = "https://api.twitch.tv/helix/videos?id=" + source_video_id
    status.set_html_status(f"GET {videos_url}")
    response = requests.get(videos_url, headers=headers).json()
    source_video = response["data"][0]
    source_video_start_epoch = int(dateutil.parser.parse(source_video["created_at"]).timestamp())
    source_video_offset = int(clip["vod_offset"]) - int(clip["duration"])
    timestamped_link = "https://www.twitch.tv/videos/" + source_video_id + "?t=" + Timestamp(source_video_offset).hh_mm_ss


    clip_start = datetime.fromtimestamp(source_video_start_epoch + source_video_offset)
    vods = []

    for i, user_id in enumerate(user_ids):
        videos_url = "https://api.twitch.tv/helix/videos?user_id=" + user_id + "&type=archive"
        status.set_html_status(f"GET {videos_url}")
        response = requests.get(videos_url, headers=headers).json()
        videos = response["data"]

        needle_vod = None
        for video in videos:
            video_start_epoch = int(dateutil.parser.parse(video["created_at"]).timestamp())
            duration = twitch_duration_string_to_seconds(video["duration"])
            video_end_epoch = video_start_epoch + duration
            if clip_start.timestamp() >= video_start_epoch and clip_start.timestamp() <= video_end_epoch:
                vod_offset = int(clip_start.timestamp() - video_start_epoch)
                video["vod_offset"] = vod_offset
                hh_mm_ss = Timestamp(vod_offset).hh_mm_ss
                timestamped_link = "https://www.twitch.tv/videos/" + video["id"] + "?t=" + hh_mm_ss
                video["timestamped_link"] = timestamped_link
                needle_vod = {
                    "user_name": video["user_name"],
                    "user_id": user_id,
                    "epoch": video_start_epoch,
                    "timestamped_link": timestamped_link,
                }
                break
        vods.append(needle_vod)
    for vod, user in zip(vods, users):
        if vod is None:
            print(f"User {user} does not have a VOD that matches the clip start time.")
        else:
            print(f"Found VOD for {user}: {vod['timestamped_link']}")
    D = {
        "clip": clip,
        "source_video": source_video,
        "vods": vods
    }
    return D

def jinja_html_endpoint(clip_id, users):
    D = manual_clip_to_synced_vods(clip_id, users)
    jinja_html = """
    <div clas="tall">
        {% for vod in D["vods"] %}
        <div class="wide">
            <a href="{{ vod['timestamped_link'] }}">{{ vod['user_name'] }}</a>
        </div>
    </div>
    """
    return jinja_html

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("clip_id", type=str)
    parser.add_argument("users", nargs="+")
    args = parser.parse_args()
    D = manual_clip_to_synced_vods(args.clip_id, args.users)
    ic(D)

if __name__ == "__main__":
    with handler():
        main()

# run.vim: term python % UnsightlyGlamorousSkunkPhilosoraptor--xusu9ybE5S5OBtn acie xchocobars
