import sys
import requests
import json
import diskcache
from waivek import ic, rel2abs, read, write
from jsonfile import usable

def query_video_info(video_id):
    cache = diskcache.Cache(rel2abs('data/video_info_cache'))
    if video_id in cache:
        return cache[video_id]
    url = 'https://gql.twitch.tv/gql'
    headers = {
        'Client-ID': 'kimne78kx3ncx6brgo4mv6wki5h1ko',  # This is a public client ID
        'Content-Type': 'application/json'
    }
    
    query = '''
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
    '''
    
    variables = {
        'videoID': video_id
    }
    
    payload = json.dumps({
        'query': query,
        'variables': variables
    })
    
    response = requests.post(url, headers=headers, data=payload)
    data = response.json()
    if data['data']['video'] is None:
        print("[query_video_info] No video info found or an error occurred.")
        return None
    
    cache[video_id] = data['data']['video']
    return cache[video_id]

def format_timestamp(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def write_chapters(video_id):
    video_info = query_video_info(video_id)
    if not video_info:
        print("[write_chapters] No video info found or an error occurred.")
        return None
    
    duration = video_info['lengthSeconds']
    chapters = []
    for edge in video_info['moments']['edges']:
        node = edge['node']
        chapters.append({
            'description': node['description'],
            'timestamp': node['positionMilliseconds'] // 1000  # Convert to seconds
        })
    
    if not chapters:
        print("[write_chapters] No chapters found.")
        return None
    
    table = []
    for chapter1, chapter2 in zip(chapters, chapters[1:] + [{'timestamp': duration}]):
        D = {}
        D['start'] = chapter1['timestamp']
        D['end'] = chapter2['timestamp']
        D['title'] = chapter1['description']
        table.append(D)
    
    if not usable("data/chapters.json"):
        write({}, "data/chapters.json")
    chapters_data = read("data/chapters.json")
    chapters_data[video_id] = table
    path = write(chapters_data, "data/chapters.json")
    print(f"Wrote {len(table)} chapters of video {video_id} to {path}")
    return table

if __name__ == "__main__":
    video_id = sys.argv[1]
    chapters = write_chapters(video_id)
    if chapters:
        print(f"Chapters for video {video_id}:")
        for chapter in chapters:
            start = format_timestamp(chapter['start'])
            end = format_timestamp(chapter['end'])
            print(f"{start} - {end}: {chapter['title']}")
    else:
        print("No chapters found or an error occurred.")

# run.vim: vert term python % 2275101544
