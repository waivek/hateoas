import os
from waivek import Timer, Timestamp, read, write   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs

from worker_utils import get_graph_payloads_downloads_folder, get_offsets_downloads_folder
import pandas as pd

def get_offsets(video_id):
    offsets_path = os.path.join(get_offsets_downloads_folder(), f"{video_id}.json")
    offsets = read(offsets_path)
    return offsets

def to_url(int_offset, video_id="1"):
    return "https://www.twitch.tv/videos/"+video_id+"?t="+Timestamp(int_offset).hh_mm_ss

def get_top_unique_indices(series, threshold=30, n=50):
    series = list(series.items())    
    stack = [series[0]]
    for index, int_offset in series[1:]:
        smallest_difference = min(abs(added_offset-int_offset) for _, added_offset in stack)
        if smallest_difference > threshold:
            stack.append((index, int_offset))
            if len(stack) == n:
                break
    indices_only = [ T[0] for T in stack ]
    return indices_only

def stats(video_id):
    offsets = get_offsets(video_id)
    # pd.options.mode.chained_assignment = None  # default='warn'
    df = pd.DataFrame()
    df["offset"] = offsets
    df["int_offset"] = df["offset"].apply(int)
    count_df = df.groupby("int_offset").count().rename(columns={"offset": "count"}).reset_index()
    rolling_size = 10
    count_df["rolling"] = count_df["count"].rolling(rolling_size).mean()
    count_df["url"] = count_df["int_offset"].apply(lambda offset: to_url(offset-rolling_size, video_id=video_id))
    count_df["timestamp"] = count_df["int_offset"].apply(lambda offset: Timestamp(offset).timestamp)

    temp_df = count_df.sort_values(["rolling"], ascending=False)
    top_unique_indices = get_top_unique_indices(temp_df["int_offset"])
    unique_filter = temp_df.index.isin(top_unique_indices)
    top_df = temp_df[unique_filter]

    # moment (commented) {{{
    # moment_count = 50
    # table = []
    # for i in range(moment_count):
    #     try:
    #         table.append(get_moment_pair(i, count_df, top_df))
    #     except Exception as error:
    #         print(error)
    #         print(f"ERROR: Index: {i}")
    #         continue
    # table = [ { "start_offset": D["peak_start_offset"], "peak_offset": D["peak_max_offset"] } for D in table ] 
    # }}}


    import math
    pairs_df = count_df[['int_offset', 'rolling']]
    pairs_df = pairs_df.replace({math.nan:None})
    assert isinstance(pairs_df, pd.DataFrame)
    # pairs_df = pairs_df.where(pd.notna(pairs_df), None)
    countpairs = pairs_df.to_dict('records')

    int_offset_series = top_df['int_offset']
    assert isinstance(int_offset_series, pd.Series)
    top_offsets = int_offset_series.to_list()
    # video_clips = get_clips(video_id)
    video_clips = []
    

    json_path = os.path.join(get_graph_payloads_downloads_folder(), f"{video_id}.json")
    payload = {
        "top_offsets": top_offsets,
        "countpairs": countpairs,
        "video_clips": video_clips
    }

    write(payload, json_path)
    table = read(json_path)
    return table

def main():
    video_id = "2199695545"
    stats(video_id)

if __name__ == "__main__":
    main()

