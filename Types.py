
from dataclasses import dataclass
from dbutils import Connection

connection = Connection("data/main.db")
videos_connection = Connection("data/videos.db")

def hhmmss(value):
    from waivek import Timestamp
    timestamp = Timestamp(value)
    return timestamp.hh_mm_ss

class PortionUrl:

    def __init__(self, id, portion_id, url, selected, user_id):
        self.id = id
        self.portion_id = portion_id
        self.url = url
        self.selected = selected
        self.user_id = user_id

    def offset(self):
        cursor = connection.execute("SELECT epoch FROM portions WHERE id = ?", (self.portion_id,))
        epoch = cursor.fetchone()[0]
        cursor = videos_connection.execute("SELECT created_at_epoch FROM videos WHERE url = ?", (self.url,))
        created_at_epoch = cursor.fetchone()[0]
        difference = epoch - created_at_epoch
        assert difference >= 0, f"Epoch is less than created_at_epoch: {difference}"
        return difference
        
    def __getitem__(self, key):
        return getattr(self, key)

class Portion:
    def __init__(self, id, sequence_id, title, epoch, duration, user_id, order):
        self.id = id
        self.sequence_id = sequence_id
        self.title = title
        self.epoch = epoch
        self.duration = duration
        self.user_id = user_id
        self.order = order

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM portionurls WHERE portion_id = ?", (id,))
        self.portionurls = [PortionUrl(**portionurl) for portionurl in cursor.fetchall()]

    def pretty(self):
        portionurl = next(pu for pu in self.portionurls if pu.user_id == self.user_id)
        video_id = portionurl.url.replace("https://www.youtube.com/watch?v=", "").replace("https://www.twitch.tv/videos/", "")
        cursor = videos_connection.cursor()
        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        video = dict(cursor.fetchone())
        user_name = video["user_name"]
        offset = self.epoch - video["created_at_epoch"]
        # return f"Portion by: {user_name}, with a duration of: {self.duration} on video: {video_id} offset: {offset}"
        selected_url_count = len([pu for pu in self.portionurls if pu.selected])
        total_url_count = len(self.portionurls)
        return f"Portion({user_name}, {self.duration}s, {video_id} @ {hhmmss(offset)}, {selected_url_count}/{total_url_count} URLs selected)"


    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        return f"Potion(id={repr(self.id)}, sequence_id={repr(self.sequence_id)}, title={repr(self.title)}, epoch={repr(self.epoch)}, duration={repr(self.duration)}, user_id={repr(self.user_id)}, order={repr(self.order)})"

class Sequence:
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM portions WHERE sequence_id = ?", (id,))
        self.portions = [Portion(**portion) for portion in cursor.fetchall()]



    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        return f"Sequence(id={repr(self.id)}, name={repr(self.name)}, description={repr(self.description)})"
