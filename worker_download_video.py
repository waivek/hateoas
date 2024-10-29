
from waivek import Connection
from portionurl_to_download_path import downloaded
from download_portionurl import download_portionurl
from worker_single import worker_single

connection = Connection("data/main.db")

def get_portionurl_id():
    # get_portionurl_id {{{
    global connection
    cursor = connection.execute("SELECT id FROM portionurls WHERE selected = 1;")
    portionurl_ids = [ id for id, in cursor.fetchall() if not downloaded(id) ]
    if portionurl_ids:
        return portionurl_ids[0]
    return None
    # }}}

def main():
    worker_single(get_portionurl_id, download_portionurl)

if __name__ == "__main__":
    main()
