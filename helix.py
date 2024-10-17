from waivek import Timer   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
from auth import get_helix_client_id_and_oath_token
import requests

class Helix:

    def __init__(self):
        client_id, oath_token = get_helix_client_id_and_oath_token()
        self.headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {oath_token}'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get(self, url):
        return self.session.get(url)

def main():
    pass

if __name__ == "__main__":
    with handler():
        main()
