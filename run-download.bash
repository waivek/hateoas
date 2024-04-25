#/bin/bash

# create a lock to prevent multiple instances of this script
if [ -f /tmp/run-download.lock ]; then
  echo "Script is already running."
  exit 1
fi

touch /tmp/run-download.lock

./refresh-downloads-db.bash

portionurl_ids=$(sqlite3 data/main.db "SELECT portionurl_id FROM downloads WHERE status = 'pending' LIMIT 5;")
echo "portionurl_ids: $portionurl_ids"
sqlite3 data/main.db "UPDATE downloads SET status = 'downloading' WHERE status = 'pending' LIMIT 5;"

# pass portionurl_ids to python ./download_portionurl.py via xargs
echo $portionurl_ids | xargs -n 1 -P 5 python ./download_portionurl.py 2>&1

./refresh-downloads-db.bash

rm /tmp/run-download.lock

exit 0
