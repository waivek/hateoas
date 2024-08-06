
import json
import os

def append_data_to_part_file(file_path: str, D: dict):
    with open(file_path, 'a') as f:
        f.write(json.dumps(D) + '\n')

def get_last_offset_from_part_file(file_path):
    with open(file_path, 'r') as f:
        last_line = f.readlines()[-1]
    D = json.loads(last_line)
    offset = D['edges'][-1]['node']['contentOffsetSeconds']
    return offset

def part_file_to_json(file_path) -> list:
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    L = [ json.loads(line) for line in lines ]
    
    return L

def video_id_to_pct(video_id: str) -> float:
    from video_utils import get_video_duration_by_id_from_database
    from worker_utils import get_chat_downloads_folder
    file_path = os.path.join(get_chat_downloads_folder(), f"{video_id}.json.part")
    offset = get_last_offset_from_part_file(file_path)
    duration = get_video_duration_by_id_from_database(video_id)
    pct = offset / duration * 100
    return pct
