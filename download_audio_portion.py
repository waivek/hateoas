import os
import sys
from waivek import Timer, Timestamp, unpack   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
from waivek import log
import glob


# constants {{{
def get_audio_downloads_folder():
    return rel2abs("static/downloads/audios")

def get_transcriptions_folder():
    return rel2abs("static/downloads/transcriptions")

def get_table():
    return [
        { 'offset': '01h28m08s', 'video_id': '2199687421', 'username': 'quarterjade' },
        { 'offset': '06h52m18s', 'video_id': '2199424572', 'username': 'sydeon' },
        # 2198842566 quarterjade 00h18m21s
        # 2198727507 02h44m10s Sydeon
        { 'offset': '00h18m21s', 'video_id': '2198842566', 'username': 'quarterjade' },
        { 'offset': '02h44m10s', 'video_id': '2198727507', 'username': 'sydeon' },

    ]
# }}}

# downloader {{{
def delete_audio_files():
    audio_downloads_folder = get_audio_downloads_folder()
    paths = glob.glob(f"{audio_downloads_folder}/*")
    for path in paths:
        os.remove(path)
        log(f"<red><bold>DELETE</bold></red> {path}")
    log("delete_audio_files() <black><RED><bold> EXIT </bold></RED></black>\n")
    sys.exit(0)

def colon_timestamp(seconds):
    assert seconds >= 0, f"[colon_timestamp] seconds is negative: {seconds}"
    timestamp = Timestamp(seconds).timestamp
    return timestamp

def get_mp3_filepath(video_id: str, offset: int, duration: int):
    audio_downloads_folder = get_audio_downloads_folder()
    offset_hhmmss = Timestamp(offset).hh_mm_ss
    # create audio filename using all arguments:
    audio_filename = f"{video_id}_{offset_hhmmss}_{duration}s"
    audio_filepath = f"{audio_downloads_folder}/{audio_filename}.mp3"
    return audio_filepath

def download_audio(video_id: str, offset: int, duration: int):
    # create audio filename using all arguments:
    audio_filepath = get_mp3_filepath(video_id, offset, duration)
    if os.path.exists(audio_filepath):
        log(f"<yellow><bold>SKIP</bold></yellow> {audio_filepath}")
        return 0
    # download audio
    url = f"https://www.twitch.tv/videos/{video_id}"
    start = colon_timestamp(offset)
    end = colon_timestamp(offset + duration)
    args = f'--download-sections "*{start}-{end}"'
    ic(audio_filepath)
    command = f"yt-dlp -x --audio-format mp3 {url} -o '{audio_filepath}' {args} --force-keyframes-at-cuts"
    exit_code = os.system(command)
    if exit_code == 0:
        if os.path.exists(audio_filepath):
            log(f"<green><bold>DOWNLOAD</bold></green> {audio_filepath}")
        else:
            log(f"<red><bold>FAILED</bold></red> {os.path.basename(audio_filepath)} (exit_code=0, but file not found)")
    else:
        log(f"<red><bold>FAILED</bold></red> {os.path.basename(audio_filepath)}")
    return exit_code
# }}}

def runner_downloader(DURATION):
    # delete_audio_files()
    table = get_table()
    for row in table:
        username, video_id, offset = unpack(row)
        download_audio(video_id, Timestamp(offset).seconds, DURATION)

def transcribe_audio(audio_filepath):
    transcription_extension = "tsv"
    transcription_filename = os.path.basename(audio_filepath).replace('.mp3', f'.{transcription_extension}')
    transcription_filepath = f"{get_transcriptions_folder()}/{transcription_filename}"
    transcription_dir = os.path.dirname(transcription_filepath)
    if os.path.exists(transcription_filepath):
        log(f"<yellow><bold>SKIP</bold></yellow> {transcription_filepath}")
        return 0
    if not os.path.exists(transcription_dir):
        raise FileNotFoundError(f"Directory not found {transcription_dir}")

    import whisper
    model = whisper.load_model("tiny.en")
    result = model.transcribe(audio_filepath)
    # print(result)

    from whisper.utils import get_writer

    writer = get_writer(transcription_extension, transcription_dir)
    writer(result, transcription_filepath) # pyright: ignore[reportCallIssue]
    log(f"<green><bold>TRANSCRIBE</bold></green> {transcription_filepath}")





def main():
    # delete_audio_files()
    DURATION = 120
    runner_downloader(DURATION)
    # return

    table = get_table()
    audio_filepaths = []
    for row in table:
        username, video_id, offset = unpack(row)
        audio_filepath = get_mp3_filepath(video_id, Timestamp(offset).seconds, DURATION)
        audio_filepaths.append(audio_filepath)
    # raise_for_missing {{{
    missing_filepaths = [path for path in audio_filepaths if not os.path.exists(path)]
    if missing_filepaths:
        log("<bold><black><RED> MISSING </RED></black></bold>\n")
        for path in missing_filepaths:
            log(f"    {path}")
        log("")
        sys.exit(0)
    # }}}

    transcription_filepaths = []
    for audio_filepath in audio_filepaths:
        transcribe_audio(audio_filepath)

    # filepath1 = "/home/vivek/hateoas/static/downloads/transcriptions/2199687421_01h28m08s_120s.tsv"
    # filepath2 = "/home/vivek/hateoas/static/downloads/transcriptions/2199424572_06h52m18s_120s.tsv"




    
if __name__ == "__main__":
    with handler():
        main()
