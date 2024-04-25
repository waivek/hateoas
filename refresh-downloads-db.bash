#/bin/bash

downloading_portionurl_ids=$(sqlite3 data/main.db "SELECT portionurl_id FROM downloads WHERE status = 'downloading';")

# check if downloaded files exist, they will be downloaded to ./static/downloads/{portionurl_id}.mp4
for portionurl_id in $downloading_portionurl_ids; do
  if [ -f "static/downloads/$portionurl_id.mp4" ]; then
    sqlite3 data/main.db "UPDATE downloads SET status = 'complete' WHERE portionurl_id = $portionurl_id;"
  else
    sqlite3 data/main.db "UPDATE downloads SET status = 'pending' WHERE portionurl_id = $portionurl_id;"
  fi
done

