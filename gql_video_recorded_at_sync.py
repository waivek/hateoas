from itertools import pairwise
from zoneinfo import ZoneInfo
import timeago
from waivek import Timer   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
import requests

from datetime import datetime
def query_single_video(video_id):
    query = '''
    query {
        video(id: "%s") {
            createdAt,
            deletedAt,
            publishedAt,
            recordedAt,
            updatedAt,
            viewableAt
        }
    }
    ''' % video_id
    response = requests.post('https://gql.twitch.tv/gql', json={'query': query}, headers={'Client-ID': 'kimne78kx3ncx6brgo4mv6wki5h1ko'})
    response.raise_for_status()
    response_json = response.json()
    if 'errors' in response_json:
        errors = response_json['errors']
        ic(errors)
        return
    data = response_json['data']
    ic(data['video'])


def query_user(user_name):
    query = '''
    query {
        user(login: "%s") {
            id,
            login,
            displayName,
            stream{archiveVideo{id}title createdAt}
        }
    }
    ''' % user_name
    response = requests.post('https://gql.twitch.tv/gql', json={'query': query}, headers={'Client-ID': 'kimne78kx3ncx6brgo4mv6wki5h1ko'})
    response.raise_for_status()
    response_json = response.json()
    if 'errors' in response_json:
        errors = response_json['errors']
        ic(errors)
        return
    data = response_json['data']
    ic(data['user']['stream'])

# KEY          VALUE
#
# createdAt    2024-08-04T23:26:51Z
# deletedAt    2024-10-03T23:26:51Z
# publishedAt  2024-08-04T23:26:51Z
# recordedAt   2024-08-04T23:26:50Z
# updatedAt    2024-08-05T03:10:31Z
# viewableAt   None
#
#
# KEY           VALUE
#
# archiveVideo  {'id': '2216010776'}
# title         IMMORTAL GRIND cut the pie tap tap
# createdAt     2024-08-04T23:26:46Z

def print_datetimes_ascending():
    from waivek import log, set_verbose_stdout
    set_verbose_stdout()
    D = {
        "stream.createdAt":    "2024-08-04T23:26:51Z",
        "stream.deletedAt":    "2024-10-03T23:26:51Z",
        "stream.publishedAt":  "2024-08-04T23:26:51Z",
        "stream.recordedAt":   "2024-08-04T23:26:50Z",
        "stream.updatedAt":    "2024-08-05T03:10:31Z",
        "video.createdAt":     "2024-08-04T23:26:46Z"
    }
    table = []
    for key, value in D.items():
        dt = datetime.fromisoformat(value.replace("Z", "")).replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Kolkata"))
        human_readable = timeago.format(dt, datetime.now(ZoneInfo("UTC")))
        # print(f"{key}  {dt.isoformat()} {human_readable}")
        table.append({"key": key, "dt": dt, "human_readable": human_readable})
    table.sort(key=lambda x: x["dt"])
    for row1, row2 in pairwise(table):
        difference = row2["dt"] - row1["dt"]
        difference_string = f"Difference b/w {row1['key']} and {row2['key']}: {difference}"
        log(difference_string, level="ERROR")





def main():
    # # sydney = '2199424572'
    # # jodi = '2199687421'
    # query_single_video('2216010776')
    # query_user('quarterjade')
    print_datetimes_ascending()

if __name__ == "__main__":
    with handler():
        main()

