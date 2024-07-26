
import json

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

