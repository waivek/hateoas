import requests

# URL of the GraphQL API
url = "https://your-api-endpoint.com/graphql"

# List of video IDs you want to query
video_ids = ["2275101544"]

# GraphQL query as a string
query = """
query GetMultipleVideos($ids: [ID!]!) {
  videos(ids: $ids) {
    id
    title
    duration
    description
    thumbnailUrl
  }
}
"""

# Variables (passing the video IDs as input)
variables = {
    "ids": video_ids
}

# Request payload
payload = {
    "query": query,
    "variables": variables
}

# Send the request to the GraphQL API
response = requests.post(url, json=payload)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Failed to fetch data: {response.status_code}, {response.text}")

