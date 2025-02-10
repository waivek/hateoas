from waivek import handler, ic, ib ,rel2abs, read, write
from box import usable

import rich

def get_info_json_path(identifier):
    return f"tmp/{identifier}.info.json"

def write_info_json(url):
    import yt_dlp
    ydl_opts = { 'quiet': True, 'skip_download': True }
    # ydl_opts = { 'quiet': True, 'skip_download': True, 'format': 'bestaudio' }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        assert info
        ydl.download([url])
        identifier = info['id']
    output_path = write(info, get_info_json_path(identifier))
    rich.print("[black on green bold] WRITE [/] [bold]" + output_path)
    return info

def get_output_path(identifier):
    import yt_dlp
    url = "https://wwww.youtube.com/watch?v=" + identifier
    ydl_opts = { 'quiet': True, 'skip_download': True, 'load_info_json': 'abc.info.json' }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        assert info
        ydl.download([identifier])
        identifier = info['id']

def main():
    identifier = "kfchvCyHmsc"
    url = "https://wwww.youtube.com/watch?v=" + identifier
    if not usable(get_info_json_path(identifier)):
        write_info_json(url)
    output_path = get_info_json_path(identifier)
    # info = read(get_info_json_path(identifier))
    # rich.print(f"[black on blue bold] READ [/] [bold]{get_info_json_path(identifier)}")

if __name__ == "__main__":
    with handler():
        main()
