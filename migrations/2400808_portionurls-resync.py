
from waivek import Connection, ic
# db: sqlite
# add the column `resync` (integer) to the table `portionurls`

connection = Connection("../data/main.db")
cursor = connection.cursor()

cursor.execute("PRAGMA table_info(portionurls)")

# cursor.execute("ALTER TABLE portionurls ADD COLUMN resync INTEGER")
# # check if the column is added
# cursor.execute("PRAGMA table_info(portionurls)")
# ic(cursor.fetchall())

# set all the values to 0
cursor.execute("UPDATE portionurls SET resync = 0")
# check if the values are set to 0

rows = cursor.execute("SELECT * FROM portionurls").fetchall()
assert all(row['resync'] == 0 for row in rows)

connection.commit()


