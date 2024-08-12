
from waivek import db_init
from waivek import Timestamp
def get_video_duration_by_id_from_database(video_id):

    connection = db_init("data/videos.db")
    cursor = connection.cursor()
    cursor.execute("SELECT duration FROM videos WHERE id = ?;", (video_id,))
    duration_int, = cursor.fetchone()
    duration_string = str(duration_int)
    if 'm' not in duration_string:
        duration_string = '00m' + duration_string
    if 'h' not in duration_string:
        duration_string = '00h' + duration_string
    seconds = Timestamp(duration_string).seconds
    return seconds
