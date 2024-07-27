
import json
import gzip
import os
import sys

def read_json_gz_file(file_path: str) -> list | dict:
    frame = sys._getframe(0)
    prefix = "{0}:{1}".format(os.path.basename(__file__), frame.f_code.co_name)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f'{prefix} File not found: {file_path}')
    if os.path.getsize(file_path) == 0:
        raise ValueError(f'{prefix} File is empty: {file_path}')

    with gzip.open(file_path, 'rt') as f:
        obj = json.load(f)
    assert isinstance(obj, list) or isinstance(obj, dict)
    return obj

