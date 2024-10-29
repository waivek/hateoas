
import os
import sys
import json
from waivek.reltools import pathjoin

def usable(json_file_path):
    """
    Returns True if
    1. If the file exists
    2. If the file is not empty
    3. If the file is a valid JSON file
    """
    path = json_file_path if os.path.isabs(json_file_path) else pathjoin(sys._getframe(1), json_file_path)
    if not os.path.exists(json_file_path):
        return False
    if os.stat(json_file_path).st_size == 0:
        return False
    try:
        with open(path, "r") as f:
            obj = json.load(f)
    except json.JSONDecodeError as e:
        return False
    return True
