import sys
import requests
import json
import diskcache
from waivek import ic, rel2abs, read, write
from get_gateway import get_anonymous_session
from box import usable
from worker_utils import get_chapters_folder

def query_video_info(video_ids):
    """Query video information for multiple video IDs in parallel."""
    cache = diskcache.Cache(rel2abs('data/video_info_cache'))
    results = {}
    videos_to_fetch = []

    # Check cache first
    for video_id in video_ids:
        if video_id in cache:
            results[video_id] = cache[video_id]
        else:
            videos_to_fetch.append(video_id)

    if not videos_to_fetch:
        return results

    # Construct batch query for remaining videos
    url = 'https://gql.twitch.tv/gql'
    headers = {
        'Client-ID': 'kimne78kx3ncx6brgo4mv6wki5h1ko',
        'Content-Type': 'application/json'
    }

    # Create a query for each video
    queries = []
    for idx, video_id in enumerate(videos_to_fetch):
        queries.append({
            'operationName': 'VideoInfo',
            'query': '''
            query VideoInfo($videoID: ID!) {
                video(id: $videoID) {
                    lengthSeconds
                    moments(momentRequestType: VIDEO_CHAPTER_MARKERS) {
                        edges {
                            node {
                                description
                                positionMilliseconds
                            }
                        }
                    }
                }
            }
            ''',
            'variables': {
                'videoID': video_id
            }
        })

    # Make single batch request
    session = get_anonymous_session(url)
    session.headers.update(headers)
    response = requests.post(url, headers=headers, json=queries)
    data = response.json()

    # Process responses
    for idx, video_id in enumerate(videos_to_fetch):
        if isinstance(data, list) and data[idx]['data']['video'] is not None:
            cache[video_id] = data[idx]['data']['video']
            results[video_id] = data[idx]['data']['video']
        else:
            print(f"[query_video_info] No video info found for video ID: {video_id}", flush=True)

    return results

def format_timestamp(seconds):
    """Convert seconds to HH:MM:SS format."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def process_video_chapters(video_id, video_info):
    """Process chapters for a single video."""

    duration = video_info['lengthSeconds']
    chapters = []
    for edge in video_info['moments']['edges']:
        node = edge['node']
        chapters.append({
            'description': node['description'],
            'timestamp': node['positionMilliseconds'] // 1000
        })

    table = []
    for chapter1, chapter2 in zip(chapters, chapters[1:] + [{'timestamp': duration}]):
        table.append({
            'start': chapter1['timestamp'],
            'end': chapter2['timestamp'],
            'title': chapter1['description']
        })

    return table

def write_chapters_and_return_results(video_ids):
    """Write chapters for multiple videos."""
    if isinstance(video_ids, str):
        video_ids = [video_ids]

    # Fetch all video info in one batch
    videos_info = query_video_info(video_ids)

    # Process chapters for all videos
    results = {}
    for video_id in video_ids:
        if video_id in videos_info:
            chapters = process_video_chapters(video_id, videos_info[video_id])
            results[video_id] = chapters

    if results:
        import rich
        chapters_folder = get_chapters_folder()
        for video_id, chapters in results.items():
            filename = f"{chapters_folder}/{video_id}.json"
            write(chapters, filename)
            rich.print("[black on green bold] WRITE [/]", filename, flush=True)

    return results

def write_chapters(video_id) -> int:
    try:
        results = write_chapters_and_return_results(video_id)
    except Exception as e:
        print(f"[write_chapters] Error: {e}", flush=True)
        return 1
    return 0

def display_chapters(chapters_dict):
    """Display chapters for multiple videos."""
    for video_id, chapters in chapters_dict.items():
        if chapters:
            print(f"\nChapters for video {video_id}:", flush=True)
            for chapter in chapters:
                start = format_timestamp(chapter['start'])
                end = format_timestamp(chapter['end'])
                print(f"{start} - {end}: {chapter['title']}", flush=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python chapters.py video_id1 [video_id2 video_id3 ...]", flush=True)
        sys.exit(1)

    video_ids = sys.argv[1:]
    chapters_dict = write_chapters_and_return_results(video_ids)
    display_chapters(chapters_dict)

# run.vim: vert term python % 2275101544 2271688217 2277153699
