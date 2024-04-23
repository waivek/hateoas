import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from dbutils import Connection


def parse_schema_to_get_table_name(schema: str):
    # https://www.sqlite.org/lang_keywords.html
    import re
    assert schema.strip().lower().startswith("create table")
    schema = schema.strip()
    if not re.match("CREATE TABLE", schema, flags=re.IGNORECASE):
        raise ValueError("The schema does not start with 'CREATE TABLE'")
    # use re to do a case insensitive replacement of `create table`
    table_name = re.sub("CREATE TABLE"  , "" , schema , flags=re.IGNORECASE)

    table_name = re.sub("IF NOT EXISTS" , "" , table_name , flags=re.IGNORECASE)

    # remove everything after the first bracket, including the bracket, multiline
    table_name = re.sub(r"\(.*", "", table_name, flags=re.DOTALL).strip()

    # if the first and last characters are backticks, quotes, double quotes or brackets, remove them
    delimiters = ["`", "'", '"', "[", "]"]
    if table_name[0] in delimiters and table_name[-1] in delimiters:
        table_name = table_name[1:-1]

    return table_name


def change_table_schema(connection, schema):
    table = parse_schema_to_get_table_name(schema)

    # connection.execute(f"CREATE TABLE temp AS SELECT * FROM {table}")
    connection.execute(f"DROP TABLE {table}")
    connection.execute(schema)
    connection.execute(f"INSERT INTO {table} SELECT * FROM temp")
    connection.execute("DROP TABLE temp")
    connection.commit()

    

schema = """
CREATE TABLE "portionurls" (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    portion_id INTEGER NOT NULL, 
    url TEXT NOT NULL, 
    selected INTEGER NOT NULL, 
    user_id TEXT NOT NULL, FOREIGN KEY(portion_id) REFERENCES portions(id) ON DELETE CASCADE, UNIQUE(portion_id, url)
);
"""
connection = Connection("data/main.db")
change_table_schema(connection, schema)

