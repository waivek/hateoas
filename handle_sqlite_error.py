

from sqlite3.dbapi2 import Error, DataError, DatabaseError, InternalError, IntegrityError, InterfaceError, OperationalError, ProgrammingError, NotSupportedError

def handle_sqlite_error(error: Error) -> None:

    if isinstance(error, DataError):
        print("DataError:", error)
    elif isinstance(error, DatabaseError):
        print("DatabaseError:", error)
    elif isinstance(error, InternalError):
        print("InternalError:", error)
    elif isinstance(error, IntegrityError):
        print("IntegrityError:", error)
    elif isinstance(error, InterfaceError):
        print("InterfaceError:", error)
    elif isinstance(error, OperationalError):
        print("OperationalError:", error)
    elif isinstance(error, ProgrammingError):
        print("ProgrammingError:", error)
    elif isinstance(error, NotSupportedError):
        print("NotSupportedError:", error)
    else:
        print("Error:", error)

