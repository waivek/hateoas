
from dbutils import Connection
from waivek import ic
connection = Connection(":memory:")
schema = "CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT, fruit TEXT NOT NULL);"
fruits = [ "apple", "banana", "cherry", "date", "elderberry" ]
connection.execute(schema)
for fruit in fruits:
    cursor = connection.execute("INSERT INTO test (fruit) VALUES (?)", (fruit,))

# delete 'cherry'
connection.execute("DELETE FROM test WHERE fruit = 'cherry';")

# select rowid, id, fruit for all
cursor = connection.execute("SELECT rowid, id, fruit FROM test;")
table = [ (rowid, id, fruit) for rowid, id, fruit in cursor ]

ic(table)
